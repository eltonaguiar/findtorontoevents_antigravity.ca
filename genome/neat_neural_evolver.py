"""
NEAT-Style Neural DNA Evolution Engine
======================================

Evolves neural network topologies and weights for trading strategies.
Unlike fixed-topology neural nets, this evolves the structure itself.

Key innovations:
- Neuro-evolution of augmenting topologies (NEAT)
- Evolves both network structure AND weights
- Species-based evolution to protect innovation
- Historical markings for crossover alignment
"""

import copy
import hashlib
import json
import logging
import random
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np

# Import base classes
from genome.genetic_programmer import OHLCVData, fetch_market_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("NEAT_Evolver")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(__file__).resolve().parent / "neat_evolver.db"
PICKS_OUTPUT = PROJECT_ROOT / "genome" / "data" / "neat_active_picks.json"


# =============================================================================
# Neural Network Genome
# =============================================================================

@dataclass
class NeuralGene:
    """A single gene representing a connection in the neural network"""
    innovation_id: int  # Global historical marker
    from_node: int
    to_node: int
    weight: float
    enabled: bool = True
    
    def copy(self) -> 'NeuralGene':
        return NeuralGene(
            innovation_id=self.innovation_id,
            from_node=self.from_node,
            to_node=self.to_node,
            weight=self.weight,
            enabled=self.enabled
        )


@dataclass
class NeuralNode:
    """A node in the neural network"""
    id: int
    node_type: str  # 'input', 'hidden', 'output', 'bias'
    activation: str = 'tanh'  # 'tanh', 'relu', 'sigmoid', 'leaky_relu'
    layer: int = 0  # For feed-forward ordering
    
    def activate(self, x: float) -> float:
        if self.activation == 'tanh':
            return np.tanh(x)
        elif self.activation == 'relu':
            return max(0, x)
        elif self.activation == 'leaky_relu':
            return x if x > 0 else 0.01 * x
        elif self.activation == 'sigmoid':
            return 1 / (1 + np.exp(-x))
        return np.tanh(x)


@dataclass
class NeuralGenome:
    """A complete neural network genotype"""
    genome_id: str
    nodes: Dict[int, NeuralNode] = field(default_factory=dict)
    genes: List[NeuralGene] = field(default_factory=list)
    fitness: float = 0.0
    adjusted_fitness: float = 0.0
    species_id: Optional[int] = None
    generation: int = 0
    parents: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.nodes:
            self._init_base_topology()
    
    def _init_base_topology(self):
        """Initialize with minimal topology (inputs + outputs)"""
        # Input nodes (26 features)
        input_features = [
            'open', 'high', 'low', 'close', 'volume',
            'rsi_14', 'rsi_2', 'ema_9', 'ema_21', 'ema_50',
            'bb_upper', 'bb_lower', 'bb_pctb',
            'macd', 'macd_signal', 'macd_hist',
            'atr_14', 'obv', 'vwap',
            'pct_1', 'pct_3', 'pct_7',
            'vol_ratio', 'funding_skew', 'depth_imbalance',
            'bias'  # Bias node
        ]
        
        for i, feat in enumerate(input_features):
            node_type = 'bias' if feat == 'bias' else 'input'
            self.nodes[i] = NeuralNode(id=i, node_type=node_type, layer=0)
        
        # Output nodes (2: buy_signal, sell_signal)
        self.nodes[100] = NeuralNode(id=100, node_type='output', activation='tanh', layer=999)
        self.nodes[101] = NeuralNode(id=101, node_type='output', activation='tanh', layer=999)
    
    def forward(self, inputs: Dict[str, float]) -> Tuple[float, float]:
        """Forward pass through the network"""
        node_values = {}
        
        # Set input values
        for node_id, node in self.nodes.items():
            if node.node_type == 'input':
                feat_name = list(inputs.keys())[node_id] if node_id < len(inputs) else 'close'
                node_values[node_id] = inputs.get(feat_name, 0.0)
            elif node.node_type == 'bias':
                node_values[node_id] = 1.0
        
        # Calculate layers
        layers = self._calculate_layers()
        
        # Process each layer
        for layer_idx in sorted(layers.keys()):
            if layer_idx == 0:
                continue  # Inputs already set
            
            for node_id in layers[layer_idx]:
                # Sum weighted inputs from enabled connections
                total = 0.0
                for gene in self.genes:
                    if gene.to_node == node_id and gene.enabled and gene.from_node in node_values:
                        total += node_values[gene.from_node] * gene.weight
                
                # Activate
                if node_id in self.nodes:
                    node_values[node_id] = self.nodes[node_id].activate(total)
        
        buy_signal = node_values.get(100, 0.0)
        sell_signal = node_values.get(101, 0.0)
        
        return buy_signal, sell_signal
    
    def _calculate_layers(self) -> Dict[int, List[int]]:
        """Calculate feed-forward layer assignments"""
        layers = {0: []}
        for node_id, node in self.nodes.items():
            if node.node_type in ('input', 'bias'):
                layers[0].append(node_id)
            else:
                if node.layer not in layers:
                    layers[node.layer] = []
                layers[node.layer].append(node_id)
        return layers
    
    def mutate_add_node(self, innovation_counter: List[int]) -> bool:
        """Add a new node by splitting an existing connection"""
        enabled_genes = [g for g in self.genes if g.enabled]
        if not enabled_genes:
            return False
        
        # Pick random gene to split
        gene = random.choice(enabled_genes)
        gene.enabled = False
        
        # Create new node
        new_node_id = max(self.nodes.keys()) + 1 if self.nodes else 200
        new_node = NeuralNode(id=new_node_id, node_type='hidden', layer=0)
        self.nodes[new_node_id] = new_node
        
        # Create two new connections
        innovation_counter[0] += 1
        gene1 = NeuralGene(
            innovation_id=innovation_counter[0],
            from_node=gene.from_node,
            to_node=new_node_id,
            weight=1.0
        )
        
        innovation_counter[0] += 1
        gene2 = NeuralGene(
            innovation_id=innovation_counter[0],
            from_node=new_node_id,
            to_node=gene.to_node,
            weight=gene.weight
        )
        
        self.genes.extend([gene1, gene2])
        return True
    
    def mutate_add_connection(self, innovation_counter: List[int]) -> bool:
        """Add a new connection between unconnected nodes"""
        possible_connections = []
        
        for from_id, from_node in self.nodes.items():
            if from_node.node_type == 'output':
                continue
            for to_id, to_node in self.nodes.items():
                if to_node.node_type in ('input', 'bias'):
                    continue
                if from_id == to_id:
                    continue
                
                # Check if connection already exists
                exists = any(g.from_node == from_id and g.to_node == to_id for g in self.genes)
                if not exists:
                    possible_connections.append((from_id, to_id))
        
        if not possible_connections:
            return False
        
        from_id, to_id = random.choice(possible_connections)
        innovation_counter[0] += 1
        
        new_gene = NeuralGene(
            innovation_id=innovation_counter[0],
            from_node=from_id,
            to_node=to_id,
            weight=random.gauss(0, 1)
        )
        self.genes.append(new_gene)
        return True
    
    def mutate_weights(self, mutation_rate: float = 0.8, perturb_rate: float = 0.9):
        """Mutate connection weights"""
        for gene in self.genes:
            if random.random() < mutation_rate:
                if random.random() < perturb_rate:
                    # Perturb
                    gene.weight += random.gauss(0, 0.5)
                else:
                    # Replace
                    gene.weight = random.gauss(0, 2)
    
    def compatibility_distance(self, other: 'NeuralGenome', c1: float = 1.0, c2: float = 1.0, c3: float = 0.4) -> float:
        """Calculate compatibility distance for speciation"""
        # Count matching, disjoint, and excess genes
        my_innovations = {g.innovation_id: g for g in self.genes}
        other_innovations = {g.innovation_id: g for g in other.genes}
        
        all_innovations = set(my_innovations.keys()) | set(other_innovations.keys())
        matching = set(my_innovations.keys()) & set(other_innovations.keys())
        
        if not matching:
            return float('inf')
        
        # Weight difference of matching genes
        weight_diff = sum(abs(my_innovations[i].weight - other_innovations[i].weight) for i in matching)
        avg_weight_diff = weight_diff / len(matching)
        
        disjoint = len([i for i in all_innovations if i < max(matching) and i not in matching])
        excess = len([i for i in all_innovations if i > max(matching)])
        
        N = max(len(self.genes), len(other.genes))
        if N < 20:
            N = 1
        
        distance = (c1 * excess / N) + (c2 * disjoint / N) + (c3 * avg_weight_diff)
        return distance


# =============================================================================
# NEAT Evolution Engine
# =============================================================================

class NEATEvolutionEngine:
    """
    NEAT-style evolution with speciation and complexification
    """
    
    def __init__(self, population_size: int = 100, target_species: int = 5):
        self.population_size = population_size
        self.target_species = target_species
        self.population: List[NeuralGenome] = []
        self.species: Dict[int, List[NeuralGenome]] = {}
        self.innovation_counter = [0]
        self.generation = 0
        self.hall_of_fame: List[NeuralGenome] = []
        
        # NEAT parameters
        self.compatibility_threshold = 3.0
        self.mutate_weight_prob = 0.8
        self.mutate_add_node_prob = 0.03
        self.mutate_add_conn_prob = 0.05
        
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(str(DB_PATH))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS neat_genomes (
                genome_id TEXT PRIMARY KEY,
                generation INTEGER,
                species_id INTEGER,
                fitness REAL,
                node_count INTEGER,
                gene_count INTEGER,
                topology_json TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS neat_evolution_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_timestamp TEXT,
                generation INTEGER,
                population_size INTEGER,
                num_species INTEGER,
                best_fitness REAL,
                avg_fitness REAL,
                avg_complexity REAL
            );
        """)
        conn.commit()
        conn.close()
    
    def initialize_population(self):
        """Create initial population with minimal topology"""
        logger.info(f"Initializing NEAT population: {self.population_size}")
        
        for i in range(self.population_size):
            genome = NeuralGenome(
                genome_id=f"neat_gen0_{i:04d}",
                generation=0
            )
            # Add some random connections to start
            for _ in range(random.randint(5, 15)):
                genome.mutate_add_connection(self.innovation_counter)
            self.population.append(genome)
        
        self._speciate()
    
    def _speciate(self):
        """Assign genomes to species based on compatibility"""
        # Clear current species
        self.species = {}
        
        for genome in self.population:
            found_species = False
            
            for species_id, members in self.species.items():
                if not members:
                    continue
                # Compare to representative (first member)
                rep = members[0]
                distance = genome.compatibility_distance(rep)
                
                if distance < self.compatibility_threshold:
                    members.append(genome)
                    genome.species_id = species_id
                    found_species = True
                    break
            
            if not found_species:
                # Create new species
                new_id = len(self.species)
                self.species[new_id] = [genome]
                genome.species_id = new_id
        
        logger.info(f"Speciation: {len(self.species)} species")
    
    def evaluate_generation(self, market_data: Dict[str, OHLCVData]):
        """Evaluate fitness of entire population"""
        logger.info(f"Evaluating generation {self.generation}")
        
        for genome in self.population:
            fitness = self._evaluate_genome(genome, market_data)
            genome.fitness = fitness
        
        # Update hall of fame
        sorted_pop = sorted(self.population, key=lambda g: g.fitness, reverse=True)
        for genome in sorted_pop[:5]:
            if genome.fitness > 0.3:
                self.hall_of_fame.append(copy.deepcopy(genome))
        
        self.hall_of_fame = sorted(self.hall_of_fame, key=lambda g: g.fitness, reverse=True)[:20]
    
    def _evaluate_genome(self, genome: NeuralGenome, market_data: Dict[str, OHLCVData]) -> float:
        """Evaluate a single genome on market data"""
        all_returns = []
        
        for symbol, data in market_data.items():
            returns = self._backtest_genome(genome, data)
            all_returns.append(returns)
        
        return np.mean(all_returns) if all_returns else 0.0
    
    def _backtest_genome(self, genome: NeuralGenome, data: OHLCVData) -> float:
        """Simple backtest for a genome"""
        # Simplified - would use actual OHLCV features
        capital = 10000.0
        position = None
        
        # Generate features for each bar
        for i in range(50, min(200, len(data.close))):
            features = {
                'open': data.open[i] / data.open[i-1] - 1,
                'high': data.high[i] / data.close[i] - 1,
                'low': data.low[i] / data.close[i] - 1,
                'close': data.close[i] / data.close[i-1] - 1,
                'volume': data.volume[i] / np.mean(data.volume[i-20:i]) if i > 20 else 1.0,
                'rsi_14': 50.0,  # Simplified
                'ema_9': data.close[i] / np.mean(data.close[i-9:i]) - 1 if i > 9 else 0,
                'ema_21': data.close[i] / np.mean(data.close[i-21:i]) - 1 if i > 21 else 0,
                'atr_14': 0.01,
                'bias': 1.0
            }
            
            buy_signal, sell_signal = genome.forward(features)
            
            # Simple logic
            if buy_signal > 0.5 and position is None:
                position = ('LONG', data.close[i])
            elif sell_signal > 0.5 and position is not None:
                entry_type, entry_price = position
                pnl = (data.close[i] - entry_price) / entry_price
                capital *= (1 + pnl * 0.5)  # 0.5x position size
                position = None
        
        total_return = (capital - 10000) / 10000
        return max(0, total_return)  # Fitness is return
    
    def reproduce(self):
        """Create next generation through speciated reproduction"""
        new_population = []
        
        # Calculate adjusted fitness (fitness / species size)
        for species_id, members in self.species.items():
            for genome in members:
                genome.adjusted_fitness = genome.fitness / len(members)
        
        # Total adjusted fitness
        total_adjusted = sum(g.adjusted_fitness for g in self.population)
        
        # Breed each species
        for species_id, members in self.species.items():
            species_adjusted = sum(g.adjusted_fitness for g in members)
            offspring_count = int((species_adjusted / total_adjusted) * self.population_size) if total_adjusted > 0 else 1
            
            # Elitism - keep best of species
            members.sort(key=lambda g: g.fitness, reverse=True)
            new_population.append(copy.deepcopy(members[0]))
            
            # Breed offspring
            for _ in range(offspring_count - 1):
                parent1 = self._tournament_select(members)
                parent2 = self._tournament_select(members)
                
                child = self._crossover(parent1, parent2)
                self._mutate(child)
                
                child.genome_id = f"neat_gen{self.generation+1}_{len(new_population):04d}"
                child.generation = self.generation + 1
                child.species_id = None
                
                new_population.append(child)
        
        self.population = new_population[:self.population_size]
        self.generation += 1
        self._speciate()
    
    def _tournament_select(self, population: List[NeuralGenome], k: int = 3) -> NeuralGenome:
        """Tournament selection"""
        tournament = random.sample(population, min(k, len(population)))
        return max(tournament, key=lambda g: g.fitness)
    
    def _crossover(self, parent1: NeuralGenome, parent2: NeuralGenome) -> NeuralGenome:
        """Crossover two genomes using innovation IDs"""
        child = NeuralGenome(
            genome_id=f"neat_cross_{random.randint(0, 9999)}",
            nodes=copy.deepcopy(parent1.nodes),
            generation=self.generation
        )
        
        # Inherit nodes from both parents
        for node_id, node in parent2.nodes.items():
            if node_id not in child.nodes:
                child.nodes[node_id] = copy.deepcopy(node)
        
        # Crossover genes
        p1_genes = {g.innovation_id: g for g in parent1.genes}
        p2_genes = {g.innovation_id: g for g in parent2.genes}
        
        child.genes = []
        for innov_id in set(p1_genes.keys()) | set(p2_genes.keys()):
            if innov_id in p1_genes and innov_id in p2_genes:
                # Matching gene - randomly inherit
                gene = random.choice([p1_genes[innov_id], p2_genes[innov_id]]).copy()
            elif innov_id in p1_genes:
                # Disjoint/excess from fitter parent
                gene = p1_genes[innov_id].copy() if parent1.fitness >= parent2.fitness else None
            else:
                gene = p2_genes[innov_id].copy() if parent2.fitness >= parent1.fitness else None
            
            if gene:
                # Disable if either parent has it disabled
                if (innov_id in p1_genes and not p1_genes[innov_id].enabled) or \
                   (innov_id in p2_genes and not p2_genes[innov_id].enabled):
                    if random.random() < 0.75:
                        gene.enabled = False
                child.genes.append(gene)
        
        return child
    
    def _mutate(self, genome: NeuralGenome):
        """Apply mutations to genome"""
        # Weight mutation
        genome.mutate_weights(self.mutate_weight_prob)
        
        # Add node
        if random.random() < self.mutate_add_node_prob:
            genome.mutate_add_node(self.innovation_counter)
        
        # Add connection
        if random.random() < self.mutate_add_conn_prob:
            genome.mutate_add_connection(self.innovation_counter)
    
    def run_evolution(self, generations: int = 20):
        """Run NEAT evolution"""
        logger.info("=" * 70)
        logger.info("NEAT NEURAL EVOLUTION STARTING")
        logger.info("=" * 70)
        
        market_data = fetch_market_data(["BTCUSDT", "ETHUSDT", "SOLUSDT"], limit=500)
        
        self.initialize_population()
        
        for gen in range(generations):
            self.evaluate_generation(market_data)
            
            best = max(self.population, key=lambda g: g.fitness)
            avg_fitness = np.mean([g.fitness for g in self.population])
            avg_complexity = np.mean([len(g.genes) for g in self.population])
            
            logger.info(f"Gen {gen:3d} | Best: {best.fitness:.4f} | "
                       f"Avg: {avg_fitness:.4f} | Species: {len(self.species)} | "
                       f"Complexity: {avg_complexity:.1f}")
            
            if gen < generations - 1:
                self.reproduce()
        
        self._save_results()
        return self.hall_of_fame[:10]
    
    def _save_results(self):
        """Save results to database and JSON"""
        now = datetime.now(timezone.utc).isoformat()
        
        # Save to DB
        conn = sqlite3.connect(str(DB_PATH))
        for genome in self.hall_of_fame[:10]:
            conn.execute(
                """INSERT OR REPLACE INTO neat_genomes
                   (genome_id, generation, species_id, fitness, node_count, gene_count, topology_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (genome.genome_id, genome.generation, genome.species_id,
                 genome.fitness, len(genome.nodes), len(genome.genes),
                 json.dumps({
                     'nodes': {k: {'type': v.node_type, 'activation': v.activation} 
                              for k, v in genome.nodes.items()},
                     'genes': [{'in': g.from_node, 'out': g.to_node, 'w': round(g.weight, 4), 'en': g.enabled}
                              for g in genome.genes]
                 }), now)
            )
        conn.commit()
        conn.close()
        
        # Export picks
        picks = []
        for i, genome in enumerate(self.hall_of_fame[:10]):
            picks.append({
                'symbol': 'BTCUSDT',
                'direction': 'LONG' if i % 2 == 0 else 'SHORT',
                'confidence': min(genome.fitness * 1.5, 1.0),
                'strategy': f"NEAT_{genome.genome_id}",
                'source_system': 'neat_neural_evolver',
                'fitness': genome.fitness,
                'complexity': len(genome.genes),
                'generation': genome.generation,
                'species': genome.species_id,
                'timestamp': now
            })
        
        output = {
            'generated_at': now,
            'system': 'neat_neural_evolver',
            'version': '1.0.0',
            'total_picks': len(picks),
            'picks': picks
        }
        
        with open(str(PICKS_OUTPUT), 'w') as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"Saved {len(picks)} NEAT picks to {PICKS_OUTPUT}")


def run_neat_evolution():
    """Entry point"""
    engine = NEATEvolutionEngine(population_size=50, target_species=5)
    winners = engine.run_evolution(generations=15)
    
    print("\n" + "=" * 70)
    print("NEAT EVOLUTION WINNERS")
    print("=" * 70)
    for i, g in enumerate(winners[:5], 1):
        print(f"{i}. {g.genome_id} | Fitness: {g.fitness:.4f} | "
              f"Nodes: {len(g.nodes)} | Genes: {len(g.genes)} | Species: {g.species_id}")
    
    return winners


if __name__ == "__main__":
    run_neat_evolution()
