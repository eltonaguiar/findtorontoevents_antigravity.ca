"""Hierarchical swarm engine with strategic -> tactical -> execution layers.

Mirrors the human analyst separation of macro outlook from security-level
execution.  Strategic signals flow to the tactical layer via the message bus;
tactical signals flow to the execution layer the same way.  A risk controller
at every layer can veto signals that exceed configured limits.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from swarms.core.base_orchestrator import BaseOrchestrator
from swarms.core.models import (
    AgentConfig,
    AgentRole,
    HierarchicalSignal,
    MemoryEntry,
    MessageType,
    SwarmMessage,
    SwarmTask,
    TaskStatus,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HierarchicalSwarmOrchestrator
# ---------------------------------------------------------------------------


class HierarchicalSwarmOrchestrator(BaseOrchestrator):
    """Hierarchical swarm with strategic -> tactical -> execution layers.

    The pipeline mirrors the way human investment teams separate concerns:

    1. **Strategic layer** — strategist agents analyse macro signals
       (market conditions, trends, regime indicators) and emit
       ``bullish`` / ``bearish`` / ``neutral`` signals per asset class.
    2. **Tactical layer** — tactician agents consume strategic signals
       and produce asset-specific predictions (``buy`` / ``sell`` / ``hold``).
    3. **Execution layer** — execution agents validate tactical signals
       against risk limits and produce execution plans (order size,
       timing, stop-loss).
    4. **Risk controller veto** — after every layer a risk controller
       reviews signals; any signal exceeding ``risk_limits`` is blocked.

    Parameters
    ----------
    memory :
        Persistent vector-store memory shared across the swarm.
    bus :
        Async pub/sub message bus.
    registry :
        Agent registry.
    safety :
        Safety enforcer.
    num_strategists :
        Number of strategist agents in the strategic layer.
    num_tacticians :
        Number of tactician agents in the tactical layer.
    risk_limits :
        Configuration dict for risk thresholds, e.g.
        ``{"max_position_size": 1000, "max_drawdown": 0.05}``.
    """

    def __init__(
        self,
        memory: Any,
        bus: Any,
        registry: Any,
        safety: Any,
        num_strategists: int = 2,
        num_tacticians: int = 3,
        risk_limits: Optional[dict] = None,
    ) -> None:
        super().__init__(memory, bus, registry, safety)
        self.num_strategists = max(1, num_strategists)
        self.num_tacticians = max(1, num_tacticians)
        self.risk_limits = risk_limits or {
            "max_position_size": 1000,
            "max_drawdown": 0.05,
            "max_concentration": 0.25,
            "min_confidence": 0.6,
        }

    # -- agent requirements ---------------------------------------------------

    def get_required_agents(self) -> list[AgentRole]:
        """Return roles: strategists + tacticians + risk_controller."""
        return (
            [AgentRole.STRATEGIST] * self.num_strategists
            + [AgentRole.TACTICIAN] * self.num_tacticians
            + [AgentRole.RISK_CONTROLLER]
        )

    # -- public entry point ---------------------------------------------------

    async def execute(self, task: SwarmTask) -> dict[str, Any]:
        """Execute a hierarchical decision-making task.

        Expected ``task.inputs`` keys:

        - ``market_data`` (*dict*) — macro indicators, indices, rates, etc.
        - ``assets`` (*list[str]*) — asset identifiers to analyse.
        - ``risk_profile`` (*str*) — one of ``"conservative"``, ``"moderate"``,
          ``"aggressive"``.

        Returns
        -------
        dict[str, Any]
            Contains ``"signals"`` — a list of serialized
            :class:`HierarchicalSignal` objects from all layers.
        """
        market_data: dict = task.inputs.get("market_data", {})
        assets: list[str] = task.inputs.get("assets", [])
        risk_profile: str = task.inputs.get("risk_profile", "moderate")

        if not assets:
            raise ValueError("Hierarchical task requires 'assets' list in inputs.")

        task.status = TaskStatus.IN_PROGRESS
        logger.info(
            "HierarchicalSwarm: processing %d assets with risk_profile='%s'",
            len(assets),
            risk_profile,
        )

        # ---- Create all agents ----------------------------------------------
        agent_ids = self.create_agents()
        strategist_ids = agent_ids[: self.num_strategists]
        tactician_ids = agent_ids[self.num_strategists : self.num_strategists + self.num_tacticians]
        risk_controller_id = agent_ids[-1]

        # ---- Phase 1: Strategic layer ---------------------------------------
        strategic_signals = await self._strategic_layer(market_data, strategist_ids)
        logger.info(
            "HierarchicalSwarm: strategic layer produced %d signals",
            len(strategic_signals),
        )

        # Risk check on strategic signals
        strategic_signals = await self._risk_check(
            strategic_signals, risk_controller_id, risk_profile
        )

        # Broadcast strategic signals to tactical layer
        for sig in strategic_signals:
            await self.bus.broadcast(
                payload={"strategic_signal": sig.model_dump()},
                sender=sig.agent_id,
                msg_type=MessageType.FINAL_OUTPUT,
            )

        # ---- Phase 2: Tactical layer ----------------------------------------
        tactical_signals = await self._tactical_layer(
            strategic_signals, assets, tactician_ids
        )
        logger.info(
            "HierarchicalSwarm: tactical layer produced %d signals",
            len(tactical_signals),
        )

        # Risk check on tactical signals
        tactical_signals = await self._risk_check(
            tactical_signals, risk_controller_id, risk_profile
        )

        # Broadcast tactical signals to execution layer
        for sig in tactical_signals:
            await self.bus.broadcast(
                payload={"tactical_signal": sig.model_dump()},
                sender=sig.agent_id,
                msg_type=MessageType.FINAL_OUTPUT,
            )

        # ---- Phase 3: Execution layer ---------------------------------------
        execution_signals = await self._execution_layer(
            tactical_signals, risk_profile, agent_ids
        )
        logger.info(
            "HierarchicalSwarm: execution layer produced %d signals",
            len(execution_signals),
        )

        # Final risk check on execution signals
        execution_signals = await self._risk_check(
            execution_signals, risk_controller_id, risk_profile
        )

        # ---- Combine and store ----------------------------------------------
        all_signals = strategic_signals + tactical_signals + execution_signals

        self.store_result(task, [s.model_dump() for s in all_signals])
        for sig in all_signals:
            entry = MemoryEntry(
                content=f"{sig.level.upper()} signal from {sig.agent_id}: {sig.signal_type} = {sig.payload}",
                metadata={
                    "level": sig.level,
                    "agent_id": sig.agent_id,
                    "signal_type": sig.signal_type,
                    "confidence": sig.confidence,
                },
                tags=["hierarchical", sig.level, sig.signal_type],
                source_swarm="hierarchical",
            )
            self.memory.add(entry)

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        return {"signals": [s.model_dump() for s in all_signals]}

    # -- Layer 1: Strategic ---------------------------------------------------

    async def _strategic_layer(
        self,
        market_data: dict,
        strategist_ids: list[str],
    ) -> list[HierarchicalSignal]:
        """Run strategist agents to analyse macro signals.

        Parameters
        ----------
        market_data :
            Dict with keys such as ``indices``, ``rates``, ``regime``, etc.
        strategist_ids :
            IDs of the strategist agents to dispatch.

        Returns
        -------
        list[HierarchicalSignal]
            One signal per strategist per asset class found in *market_data*.
        """
        tasks = [
            self._strategist_analyze(agent_id, market_data)
            for agent_id in strategist_ids
        ]
        results = await asyncio.gather(*tasks)
        signals: list[HierarchicalSignal] = []
        for sig_list in results:
            signals.extend(sig_list)
        return signals

    async def _strategist_analyze(
        self, agent_id: str, market_data: dict
    ) -> list[HierarchicalSignal]:
        r"""Have a single strategist analyse macro conditions.

        Returns a list of :class:`HierarchicalSignal`\ s — one per
        detected asset class.
        """
        await self.bus.broadcast(
            payload={
                "task": "strategic_analysis",
                "agent_id": agent_id,
                "market_data": market_data,
            },
            sender="orchestrator",
            msg_type=MessageType.TASK_ASSIGNMENT,
        )
        await asyncio.sleep(0.01)

        # Deterministic mock signals based on market_data hash
        md_hash = hash(str(market_data)) % 100
        regimes = ["bullish", "bearish", "neutral"]
        regime = regimes[md_hash % len(regimes)]
        confidence = round(0.6 + (md_hash % 30) / 100.0, 2)

        asset_classes = market_data.get("asset_classes", ["equities"])
        signals: list[HierarchicalSignal] = []
        for ac in asset_classes:
            sig = HierarchicalSignal(
                level="strategic",
                agent_id=agent_id,
                signal_type="regime",
                payload={
                    "asset_class": ac,
                    "outlook": regime,
                    "macro_score": md_hash % 100,
                },
                confidence=confidence,
                timestamp=datetime.utcnow(),
            )
            signals.append(sig)
            await self.bus.broadcast(
                payload=sig.model_dump(),
                sender=agent_id,
                msg_type=MessageType.FINAL_OUTPUT,
            )
        return signals

    # -- Layer 2: Tactical ----------------------------------------------------

    async def _tactical_layer(
        self,
        strategic_signals: list[HierarchicalSignal],
        assets: list[str],
        tactician_ids: list[str],
    ) -> list[HierarchicalSignal]:
        """Run tactician agents to produce asset-specific predictions.

        Parameters
        ----------
        strategic_signals :
            Output from the strategic layer.
        assets :
            Individual asset identifiers to evaluate.
        tactician_ids :
            IDs of the tactician agents to dispatch.

        Returns
        -------
        list[HierarchicalSignal]
            One tactical signal per (tactician, asset) pair.
        """
        tasks = []
        for asset in assets:
            for agent_id in tactician_ids:
                tasks.append(
                    self._tactician_predict(agent_id, strategic_signals, asset)
                )
        results = await asyncio.gather(*tasks)
        signals: list[HierarchicalSignal] = []
        for sig in results:
            if sig is not None:
                signals.append(sig)
        return signals

    async def _tactician_predict(
        self,
        agent_id: str,
        strategic_signals: list[HierarchicalSignal],
        asset: str,
    ) -> Optional[HierarchicalSignal]:
        """Have a single tactician predict for one asset.

        The tactical signal is conditioned on the aggregate strategic
        outlook for the asset's class.
        """
        await self.bus.broadcast(
            payload={
                "task": "tactical_prediction",
                "agent_id": agent_id,
                "asset": asset,
                "strategic_context": [s.model_dump() for s in strategic_signals],
            },
            sender="orchestrator",
            msg_type=MessageType.TASK_ASSIGNMENT,
        )
        await asyncio.sleep(0.01)

        # Derive outlook from strategic signals
        outlook = "neutral"
        for s in strategic_signals:
            if s.payload.get("asset_class") == self._infer_asset_class(asset):
                outlook = s.payload.get("outlook", "neutral")
                break

        # Deterministic mock tactical signal
        asset_hash = hash(asset) % 100
        actions = {"bullish": ["buy", "hold"], "bearish": ["sell", "hold"], "neutral": ["hold"]}
        action = actions.get(outlook, ["hold"])[asset_hash % len(actions.get(outlook, ["hold"]))]
        confidence = round(0.55 + (asset_hash % 35) / 100.0, 2)

        return HierarchicalSignal(
            level="tactical",
            agent_id=agent_id,
            signal_type="entry",
            payload={
                "asset": asset,
                "action": action,
                "outlook": outlook,
                "tactical_score": asset_hash % 100,
            },
            confidence=confidence,
            timestamp=datetime.utcnow(),
        )

    # -- Layer 3: Execution ---------------------------------------------------

    async def _execution_layer(
        self,
        tactical_signals: list[HierarchicalSignal],
        risk_profile: str,
        agent_ids: list[str],
    ) -> list[HierarchicalSignal]:
        """Run execution agents to validate and size positions.

        Parameters
        ----------
        tactical_signals :
            Output from the tactical layer.
        risk_profile :
            ``"conservative"``, ``"moderate"``, or ``"aggressive"``.
        agent_ids :
            All agent IDs (execution logic runs on the first available).

        Returns
        -------
        list[HierarchicalSignal]
            Execution signals with order sizing, timing, and stop-loss.
        """
        tasks = [
            self._execution_plan(signal, risk_profile, agent_ids[i % len(agent_ids)])
            for i, signal in enumerate(tactical_signals)
        ]
        return await asyncio.gather(*tasks)

    async def _execution_plan(
        self,
        tactical_signal: HierarchicalSignal,
        risk_profile: str,
        executor_id: str,
    ) -> HierarchicalSignal:
        """Produce an execution plan for a single tactical signal.

        Order size is scaled by risk profile and confidence.
        """
        await self.bus.broadcast(
            payload={
                "task": "execution_plan",
                "agent_id": executor_id,
                "tactical_signal": tactical_signal.model_dump(),
                "risk_profile": risk_profile,
            },
            sender="orchestrator",
            msg_type=MessageType.TASK_ASSIGNMENT,
        )
        await asyncio.sleep(0.005)

        # Risk-profile scaling
        profile_multiplier = {"conservative": 0.5, "moderate": 1.0, "aggressive": 1.5}.get(
            risk_profile, 1.0
        )

        action = tactical_signal.payload.get("action", "hold")
        confidence = tactical_signal.confidence
        asset = tactical_signal.payload.get("asset", "unknown")

        # Size based on confidence and risk profile
        base_size = 100
        order_size = int(base_size * confidence * profile_multiplier)
        order_size = min(order_size, self.risk_limits.get("max_position_size", 1000))

        # Stop-loss based on risk profile
        stop_loss_pct = {
            "conservative": 0.02,
            "moderate": 0.05,
            "aggressive": 0.10,
        }.get(risk_profile, 0.05)

        return HierarchicalSignal(
            level="execution",
            agent_id=executor_id,
            signal_type="order",
            payload={
                "asset": asset,
                "action": action,
                "order_size": order_size,
                "order_type": "limit",
                "stop_loss_pct": stop_loss_pct,
                "timing": "immediate",
                "parent_tactical": tactical_signal.model_dump(),
            },
            confidence=confidence,
            timestamp=datetime.utcnow(),
        )

    # -- Risk controller veto -------------------------------------------------

    async def _risk_check(
        self,
        signals: list[HierarchicalSignal],
        risk_controller_id: str,
        risk_profile: str,
    ) -> list[HierarchicalSignal]:
        """Risk controller reviews signals and vetoes those exceeding limits.

        A signal is **vetoed** when any of the following hold:

        - ``confidence < risk_limits["min_confidence"]``
        - Execution order size > ``risk_limits["max_position_size"]``
        - Concentration in a single asset > ``risk_limits["max_concentration"]``

        Vetoed signals have their ``payload.vetoed`` flag set to ``True`` and
        their confidence set to ``0.0``.

        Parameters
        ----------
        signals :
            Signals from the most recent layer.
        risk_controller_id :
            ID of the risk controller agent.
        risk_profile :
            Current risk profile (affects thresholds).

        Returns
        -------
        list[HierarchicalSignal]
            The (possibly modified) signal list.
        """
        await self.bus.broadcast(
            payload={
                "task": "risk_check",
                "agent_id": risk_controller_id,
                "signal_count": len(signals),
                "risk_profile": risk_profile,
            },
            sender="orchestrator",
            msg_type=MessageType.TASK_ASSIGNMENT,
        )
        await asyncio.sleep(0.005)

        # Apply risk-profile adjustment
        profile_thresholds = {
            "conservative": {"min_confidence": 0.75, "max_position_size": 500},
            "moderate": {"min_confidence": 0.60, "max_position_size": 1000},
            "aggressive": {"min_confidence": 0.45, "max_position_size": 2000},
        }
        adjusted = profile_thresholds.get(risk_profile, {})
        min_confidence = adjusted.get(
            "min_confidence", self.risk_limits.get("min_confidence", 0.6)
        )
        max_position = adjusted.get(
            "max_position_size", self.risk_limits.get("max_position_size", 1000)
        )
        max_concentration = self.risk_limits.get("max_concentration", 0.25)

        # Track concentration per asset
        asset_exposure: dict[str, int] = {}
        for sig in signals:
            asset = sig.payload.get("asset", "unknown")
            if sig.level == "execution":
                asset_exposure[asset] = asset_exposure.get(asset, 0) + sig.payload.get(
                    "order_size", 0
                )

        checked: list[HierarchicalSignal] = []
        for sig in signals:
            veto_reasons: list[str] = []

            # Confidence check
            if sig.confidence < min_confidence:
                veto_reasons.append(
                    f"confidence {sig.confidence:.2f} below threshold {min_confidence}"
                )

            # Position size check
            if sig.level == "execution":
                order_size = sig.payload.get("order_size", 0)
                if order_size > max_position:
                    veto_reasons.append(
                        f"order_size {order_size} exceeds max {max_position}"
                    )

                # Concentration check (simplified: count signals per asset)
                asset = sig.payload.get("asset", "unknown")
                total_portfolio = max(sum(asset_exposure.values()), 1)
                if asset_exposure.get(asset, 0) / total_portfolio > max_concentration:
                    veto_reasons.append(
                        f"concentration for {asset} exceeds {max_concentration:.0%}"
                    )

            if veto_reasons:
                logger.warning(
                    "HierarchicalSwarm: risk_controller vetoed signal from %s: %s",
                    sig.agent_id,
                    "; ".join(veto_reasons),
                )
                sig.payload["vetoed"] = True
                sig.payload["veto_reasons"] = veto_reasons
                sig.confidence = 0.0
            else:
                sig.payload["vetoed"] = False

            checked.append(sig)

        return checked

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _infer_asset_class(asset: str) -> str:
        """Infer the asset class from an asset identifier.

        This is a simple heuristic — in production this would use a
        proper taxonomy or reference data.
        """
        asset_lower = asset.lower()
        if any(k in asset_lower for k in ("equity", "stock", "etf", "index")):
            return "equities"
        if any(k in asset_lower for k in ("bond", "treasury", "credit")):
            return "fixed_income"
        if any(k in asset_lower for k in ("btc", "eth", "crypto")):
            return "crypto"
        if any(k in asset_lower for k in ("gold", "silver", "oil", "commodity")):
            return "commodities"
        if any(k in asset_lower for k in ("fx", "usd", "eur", "gbp")):
            return "fx"
        return "equities"  # default
