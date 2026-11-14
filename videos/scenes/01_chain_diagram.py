from manim import *
import os

config.pixel_height = 1080
config.pixel_width = 1920
config.frame_rate = 30
config.background_color = "#0d1117"

class ChainDiagram(Scene):
    def construct(self):
        # Title
        title = Text("The SAM Chain: Install → Discovery Model → Software Model → Entitlement → Result", 
                     font_size=36, color="#58a6ff").to_edge(UP, buff=0.5)
        self.play(Write(title), run_time=1.5)
        self.wait(0.5)

        # Define the chain nodes
        nodes_data = [
            ("CI\n(CMDB/IRE)", "#7ee787", "cmdb_ci"),
            ("cmdb_sam_sw_install\n(one install per device)", "#d2a8ff", "install"),
            ("cmdb_sam_sw_discovery_model\n(raw fingerprint + normalized)", "#ffa657", "discovery_model"),
            ("cmdb_software_product_model\n(purchased product profile)", "#ff7b72", "software_model"),
            ("alm_license\n(rights + metric + dates)", "#a5d6ff", "entitlement"),
            ("RECONCILIATION\n(rights vs demand)", "#ffdf5d", "recon"),
        ]

        results_data = [
            ("samp_product_result", "#7ee787"),
            ("Software Model Results", "#d2a8ff"),
            ("samp_license_metric_result", "#ffa657"),
        ]

        # Create nodes
        nodes = []
        for i, (label, color, key) in enumerate(nodes_data):
            box = RoundedRectangle(
                width=3.2, height=1.6,
                corner_radius=0.15,
                fill_color=color, fill_opacity=0.15,
                stroke_color=color, stroke_width=2
            )
            text = Text(label, font_size=20, color=color, line_spacing=1.1).move_to(box.get_center())
            group = VGroup(box, text)
            nodes.append(group)

        # Arrange horizontally
        node_group = VGroup(*nodes).arrange(RIGHT, buff=1.0).next_to(title, DOWN, buff=1.0)
        
        # Create arrows between nodes
        arrows = []
        for i in range(len(nodes) - 1):
            arrow = Arrow(
                nodes[i].get_right(), nodes[i+1].get_left(),
                buff=0.2, stroke_width=3, color="#8b949e",
                tip_length=0.2
            )
            arrows.append(arrow)

        # Create result boxes below reconciliation
        result_nodes = []
        for label, color in results_data:
            box = RoundedRectangle(
                width=3.0, height=1.0,
                corner_radius=0.1,
                fill_color=color, fill_opacity=0.1,
                stroke_color=color, stroke_width=1.5
            )
            text = Text(label, font_size=18, color=color).move_to(box.get_center())
            group = VGroup(box, text)
            result_nodes.append(group)

        result_group = VGroup(*result_nodes).arrange(RIGHT, buff=0.8)
        result_group.next_to(nodes[-1], DOWN, buff=1.2)

        # Arrows from reconciliation to results
        recon_arrows = []
        for rn in result_nodes:
            arrow = Arrow(
                nodes[-1].get_bottom() + DOWN * 0.2,
                rn.get_top(),
                buff=0.1, stroke_width=2, color="#8b949e",
                tip_length=0.15
            )
            recon_arrows.append(arrow)

        # Animate chain
        for i, node in enumerate(nodes):
            self.play(FadeIn(node, shift=UP * 0.3), run_time=0.5)
            if i < len(arrows):
                self.play(GrowArrow(arrows[i]), run_time=0.4)
            self.wait(0.2)

        # Show reconciliation highlight
        self.play(nodes[-1][0].animate.set_fill(opacity=0.3), run_time=0.5)
        self.wait(0.3)

        # Show results
        for i, rn in enumerate(result_nodes):
            self.play(FadeIn(rn, shift=UP * 0.3), GrowArrow(recon_arrows[i]), run_time=0.4)

        # Key insight text
        insight = Text(
            "Install → Discovery Model → Software Model → Entitlement → Result",
            font_size=28, color="#58a6ff", weight=BOLD
        ).next_to(result_group, DOWN, buff=1.0)
        
        self.play(Write(insight), run_time=1.0)
        self.wait(2)

        # Fade out
        all_mobjects = VGroup(title, node_group, *arrows, result_group, *recon_arrows, insight)
        self.play(FadeOut(all_mobjects), run_time=1.0)


class FourGates(Scene):
    def construct(self):
        config.background_color = "#0d1117"
        
        title = Text("The Four Gates: Prerequisites for SAM to Work", 
                     font_size=40, color="#58a6ff").to_edge(UP, buff=0.5)
        self.play(Write(title), run_time=1.0)

        gates = [
            ("1. Schema +\nEdition", "Correct plugin installed\nSAM tables present", "#7ee787"),
            ("2. CMDB +\nCI Identity", "One CI per device\nIRE rules reviewed", "#d2a8ff"),
            ("3. Discovery\nFeed", "One trusted source\npopulating installs", "#ffa657"),
            ("4. Normalization +\nEntitlements", "Models normalize\nEvery entitlement has model + metric", "#ff7b72"),
        ]

        gate_groups = []
        for i, (gate_title, desc, color) in enumerate(gates):
            box = RoundedRectangle(
                width=4.2, height=2.8,
                corner_radius=0.2,
                fill_color=color, fill_opacity=0.1,
                stroke_color=color, stroke_width=2
            )
            
            num = Text(gate_title.split(".")[0] + ".", font_size=48, color=color, weight=BOLD)
            num.move_to(box.get_top() + DOWN * 0.6 + LEFT * 1.6)
            
            g_title = Text(gate_title.split("\n")[0] + " " + gate_title.split("\n")[1], 
                          font_size=24, color=color, weight=BOLD)
            g_title.move_to(box.get_top() + DOWN * 0.6 + RIGHT * 0.3)
            
            desc_text = Text(desc, font_size=18, color="#c9d1d9", line_spacing=1.3)
            desc_text.move_to(box.get_center() + DOWN * 0.2)
            
            check = Text("✓ PASS", font_size=24, color=color, weight=BOLD).move_to(box.get_bottom() + UP * 0.5)
            check.set_opacity(0)
            
            group = VGroup(box, num, g_title, desc_text, check)
            gate_groups.append(group)

        gate_row = VGroup(*gate_groups).arrange(RIGHT, buff=0.6).next_to(title, DOWN, buff=1.0)

        # Animate gates appearing
        for i, gg in enumerate(gate_groups):
            self.play(FadeIn(gg, shift=UP * 0.5), run_time=0.6)
            self.play(gg[4].animate.set_opacity(1), run_time=0.3)  # checkmark
            self.wait(0.2)

        # Consequence text
        consequence = Text(
            "If ANY gate fails → reconciliation produces garbage data → wrong compliance position",
            font_size=24, color="#f85149", weight=BOLD
        ).next_to(gate_row, DOWN, buff=1.0)
        
        self.play(Write(consequence), run_time=1.0)
        self.wait(2)
        self.play(FadeOut(VGroup(title, gate_row, consequence)), run_time=1.0)


class NormalizationStates(Scene):
    def construct(self):
        config.background_color = "#0d1117"
        
        title = Text("Normalization Statuses: Six States (Not Four!)", 
                     font_size=38, color="#58a6ff").to_edge(UP, buff=0.5)
        self.play(Write(title), run_time=1.0)

        states = [
            ("New", "Auto-created from\ndiscovery", "No", "No", "#7ee787"),
            ("Match Not Found", "No match in\ncontent library", "Yes", "No", "#ffa657"),
            ("Publisher\nNormalized", "Matched to publisher\ncontent", "Yes", "Yes → MNF", "#d2a8ff"),
            ("Partially\nNormalized", "Partial match\n(version/edition missing)", "Yes", "Yes → MNF", "#a5d6ff"),
            ("Normalized", "Fully matched\nto software model", "No", "Yes → MNF", "#7ee787"),
            ("Manually\nNormalized", "Admin manually\nassigned model", "No", "No", "#ff7b72"),
        ]

        # Table header
        headers = ["Status", "Meaning", "Manual\nNormalize?", "Revert?", "Reverts To"]
        col_widths = [2.2, 2.8, 1.8, 1.2, 2.0]
        
        table = Table(
            [headers] + [[s[0], s[1], s[2], s[3], "Match Not Found" if s[3]=="Yes" else "—"] for s in states],
            col_widths=col_widths,
            include_outer_lines=True,
            line_config={"stroke_color": "#30363d", "stroke_width": 1},
            element_to_mobject_config={"font_size": 16}
        )
        table.scale(0.7)
        table.next_to(title, DOWN, buff=0.5)

        # Color code rows
        for i, (_, _, _, _, color) in enumerate(states):
            for j in range(len(headers)):
                cell = table.get_entries((i+1, j))
                cell.set_color(color)
                if j == 0:
                    cell.set_weight(BOLD)

        self.play(Create(table), run_time=2.0)
        
        # Highlight key insight
        insight = Text(
            "KEY: All reverts go to 'Match Not Found' • Pattern-normalized models CANNOT be reverted",
            font_size=22, color="#ffdf5d", weight=BOLD
        ).next_to(table, DOWN, buff=0.8)
        
        self.play(Write(insight), run_time=1.0)
        self.wait(2.5)
        self.play(FadeOut(VGroup(title, table, insight)), run_time=1.0)


class ReconciliationTiers(Scene):
    def construct(self):
        config.background_color = "#0d1117"
        
        title = Text("Reconciliation Results: Three Tiers", 
                     font_size=38, color="#58a6ff").to_edge(UP, buff=0.5)
        self.play(Write(title), run_time=1.0)

        tiers = [
            ("PRODUCT TIER", "samp_product_result", 
             ["Is the product compliant?", "What is the cost/savings?", "Roll-up view"],
             "#7ee787"),
            ("SOFTWARE MODEL TIER", "Software Model Results",
             ["Which model is the problem?", "Drill-down from product", "Model-level compliance"],
             "#d2a8ff"),
            ("LICENSE METRIC TIER", "samp_license_metric_result",
             ["Rights owned vs used vs available", "Per metric (user, device, core, PVU...)", "The math layer"],
             "#ffa657"),
        ]

        tier_groups = []
        for tier_name, table_name, bullets, color in tiers:
            box = RoundedRectangle(
                width=5.5, height=3.5,
                corner_radius=0.15,
                fill_color=color, fill_opacity=0.1,
                stroke_color=color, stroke_width=2
            )
            
            t_name = Text(tier_name, font_size=26, color=color, weight=BOLD)
            t_name.move_to(box.get_top() + DOWN * 0.6)
            
            t_table = Text(f"Table: {table_name}", font_size=18, color="#8b949e", font="Monospace")
            t_table.move_to(box.get_top() + DOWN * 1.1)
            
            bullet_items = VGroup(*[
                Text(f"• {b}", font_size=18, color="#c9d1d9", line_spacing=1.4)
                for b in bullets
            ]).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
            bullet_items.move_to(box.get_center() + DOWN * 0.2)
            
            group = VGroup(box, t_name, t_table, bullet_items)
            tier_groups.append(group)

        tier_row = VGroup(*tier_groups).arrange(RIGHT, buff=0.8).next_to(title, DOWN, buff=0.8)

        for tg in tier_groups:
            self.play(FadeIn(tg, shift=UP * 0.4), run_time=0.6)

        # Run record
        run_record = Text(
            "Run Record: samp_reconciliation_result  •  NO single 'sam_sw_reconciliation_result' table exists",
            font_size=20, color="#ffdf5d", weight=BOLD
        ).next_to(tier_row, DOWN, buff=0.8)
        
        self.play(Write(run_record), run_time=1.0)
        self.wait(2.5)
        self.play(FadeOut(VGroup(title, tier_row, run_record)), run_time=1.0)


class RightsAlgebra(Scene):
    def construct(self):
        config.background_color = "#0d1117"
        
        title = Text("Rights Algebra: The Core Math of Compliance", 
                     font_size=38, color="#58a6ff").to_edge(UP, buff=0.5)
        self.play(Write(title), run_time=1.0)

        equations = [
            ("Rights Owned", "= Σ active entitlements sharing the metric", "#7ee787"),
            ("Rights Used", "= Allocated In Use + Not Allocated In Use + Installed", "#ffa657"),
            ("Rights Available", "= Rights Owned − Rights Used", "#d2a8ff"),
            ("Allocated Not In Use", "= Wasted rights → REMOVE allocations", "#ff7b72"),
            ("Not Allocated In Use", "= Unallocated consumption → CREATE allocations or REMOVE installs", "#a5d6ff"),
        ]

        eq_groups = []
        for i, (name, formula, color) in enumerate(equations):
            n = Text(name, font_size=24, color=color, weight=BOLD)
            f = Text(formula, font_size=20, color="#c9d1d9", font="Monospace")
            group = VGroup(n, f).arrange(RIGHT, buff=0.5)
            eq_groups.append(group)

        eq_column = VGroup(*eq_groups).arrange(DOWN, buff=0.6, aligned_edge=LEFT)
        eq_column.next_to(title, DOWN, buff=1.0).to_edge(LEFT, buff=1.0)

        for eg in eq_groups:
            self.play(Write(eg), run_time=0.6)

        # Compliance positions
        positions = [
            ("COMPLIANT", "Rights Owned ≥ Rights Used", "#7ee787"),
            ("UNDER-LICENSED", "Rights Used > Rights Owned  (AUDIT EXPOSURE)", "#f85149"),
            ("OVER-LICENSED", "Rights Owned > Rights Used  (WASTED SPEND)", "#ffdf5d"),
        ]

        pos_groups = []
        for name, desc, color in positions:
            box = RoundedRectangle(
                width=5.5, height=1.2,
                corner_radius=0.1,
                fill_color=color, fill_opacity=0.15,
                stroke_color=color, stroke_width=2
            )
            t = Text(f"{name}: {desc}", font_size=20, color=color, weight=BOLD)
            t.move_to(box.get_center())
            group = VGroup(box, t)
            pos_groups.append(group)

        pos_column = VGroup(*pos_groups).arrange(DOWN, buff=0.3)
        pos_column.next_to(eq_column, RIGHT, buff=2.0)

        for pg in pos_groups:
            self.play(FadeIn(pg, shift=LEFT * 0.3), run_time=0.5)

        self.wait(2.5)
        self.play(FadeOut(VGroup(title, eq_column, pos_column)), run_time=1.0)


class TopTraps(Scene):
    def construct(self):
        config.background_color = "#0d1117"
        
        title = Text("Top 7 SAM Traps (Interview Gold)", 
                     font_size=38, color="#58a6ff").to_edge(UP, buff=0.5)
        self.play(Write(title), run_time=1.0)

        traps = [
            ("1. Metric Mismatch", "Model metric ≠ Entitlement metric\n→ Silently meaningless result", "#f85149"),
            ("2. Duplicate Installs", "Multiple discovery sources\n→ Inflated demand; configure dedup", "#ffa657"),
            ("3. Unnormalized Titles", "Raw titles stay 'Unlicensed/Unknown'\n→ Normalize BEFORE auto-create", "#ffdf5d"),
            ("4. Maintenance as License", "Support/maintenance treated as license\n→ False compliance position", "#ff7b72"),
            ("5. Out-of-Scope Devices", "Leased/ignored devices keep installs\n→ Phantom demand; use exclude-CI job", "#d2a8ff"),
            ("6. First Recon = Invoice", "Treating first run as true-up\n→ Use as data-quality loop instead", "#a5d6ff"),
            ("7. Dead SaaS Connector", "Connector fails silently\n→ 'No waste' illusion; monitor health", "#7ee787"),
        ]

        trap_groups = []
        for i, (name, desc, color) in enumerate(traps):
            box = RoundedRectangle(
                width=8.5, height=1.4,
                corner_radius=0.1,
                fill_color=color, fill_opacity=0.1,
                stroke_color=color, stroke_width=1.5
            )
            n = Text(name, font_size=22, color=color, weight=BOLD)
            d = Text(desc, font_size=18, color="#c9d1d9")
            content = VGroup(n, d).arrange(RIGHT, buff=0.4).move_to(box.get_center())
            group = VGroup(box, content)
            trap_groups.append(group)

        trap_column = VGroup(*trap_groups).arrange(DOWN, buff=0.25)
        trap_column.next_to(title, DOWN, buff=0.5).scale(0.9)

        for i, tg in enumerate(trap_column):
            self.play(FadeIn(tg, shift=RIGHT * 0.3), run_time=0.4)
            if i == 2:  # Pause at trap 3
                self.wait(0.3)

        self.wait(2.0)
        self.play(FadeOut(VGroup(title, trap_column)), run_time=1.0)


# Render commands:
# manim -pqh 01_chain_diagram.py ChainDiagram
# manim -pqh 01_chain_diagram.py FourGates
# manim -pqh 01_chain_diagram.py NormalizationStates
# manim -pqh 01_chain_diagram.py ReconciliationTiers
# manim -pqh 01_chain_diagram.py RightsAlgebra
# manim -pqh 01_chain_diagram.py TopTraps