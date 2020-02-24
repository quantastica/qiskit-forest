import unittest
import networkx as nx
import numpy as np
from docplex.mp.model import Model

from qiskit import BasicAer
from qiskit.aqua import aqua_globals, QuantumInstance
from qiskit.aqua.algorithms import QAOA
from qiskit.aqua.components.optimizers import SPSA
from qiskit.optimization.ising import docplex, max_cut
from qiskit.optimization.ising.common import sample_most_likely
from quantastica.qiskit_forest import ForestBackend

import time
import sys
import logging
import os
import warnings


@unittest.skipUnless(
    os.getenv("SLOW") == "1",
    "Skipping this test (environment variable SLOW must be set to 1)",
)
class TestQAOA(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(
            format='%(levelname)s %(asctime)s %(pathname)s - %(message)s',
            level=os.environ.get("LOGLEVEL", "CRITICAL"),
        )
        self.startTime = time.time()
        """
        Ignore following warning since it seems
        that there is nothing that we can do about it
        ResourceWarning: unclosed <socket.socket fd=9, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=6, laddr=('127.0.0.1', 50494), raddr=('127.0.0.1', 5000)>
        """
        warnings.filterwarnings(action="ignore",
                         category=ResourceWarning)

    def tearDown(self):
        t = time.time() - self.startTime
        sys.stderr.write(" took %.3fs ... " % (t))
        """
        Restore warnings back
        """
        warnings.filterwarnings(action="always",
                         category=ResourceWarning)

    def test_qaoa(self):
        print("Running Forest test...")
        forest_backend = ForestBackend.get_backend("qasm_simulator")
        forest_results = self.run_simulation(forest_backend)
        print("Running AER test...")
        aer_backend = BasicAer.get_backend("qasm_simulator")
        aer_results = self.run_simulation(aer_backend)
        print("===== Calculations done =====")
        print("  ==== AER Results =====")
        print(aer_results)
        print("  ==== Forest Results =====")
        print(forest_results)
        threshold = 0.9
        aer_k = abs(aer_results['maxcut_objective']/aer_results['solution_objective'])
        forest_k = abs(forest_results['maxcut_objective']/forest_results['solution_objective'])
        self.assertGreater( aer_k, threshold )
        self.assertGreater( forest_k, threshold )

    def run_simulation(self, backend):
        #
        # Random 3-regular graph with 12 nodes
        #
        n      = int(os.environ.get("N", "4"))
        graph = nx.random_regular_graph(3, n)
        for e in graph.edges():
            graph[e[0]][e[1]]['weight'] = 1.0

        # Compute the weight matrix from the graph
        w = np.zeros([n, n])
        for i in range(n):
            for j in range(n):
                temp = graph.get_edge_data(i, j, default=0)
                if temp != 0:
                    w[i, j] = temp["weight"]

        # Create an Ising Hamiltonian with docplex.
        mdl = Model(name="max_cut")
        mdl.node_vars = mdl.binary_var_list(list(range(n)), name="node")
        maxcut_func = mdl.sum(
            w[i, j] * mdl.node_vars[i] * (1 - mdl.node_vars[j])
            for i in range(n)
            for j in range(n)
        )
        mdl.maximize(maxcut_func)
        qubit_op, offset = docplex.get_operator(mdl)

        # Run quantum algorithm QAOA on qasm simulator
        seed = int(os.environ.get("SEED", "40598"))
        aqua_globals.random_seed = seed

        spsa = SPSA(max_trials=250)
        qaoa = QAOA(qubit_op, spsa, p=5, max_evals_grouped = 4)

        quantum_instance = QuantumInstance(
            backend, shots=1024, seed_simulator=seed, seed_transpiler=seed,
            optimization_level=0
        )
        result = qaoa.run(quantum_instance)

        x = sample_most_likely(result["eigvecs"][0])
        result["solution"] = max_cut.get_graph_solution(x)
        result["solution_objective"] = max_cut.max_cut_value(x, w)
        result["maxcut_objective"] = result["energy"] + offset
        """
        print("energy:", result["energy"])
        print("time:", result["eval_time"])
        print("max-cut objective:", result["energy"] + offset)
        print("solution:", max_cut.get_graph_solution(x))
        print("solution objective:", max_cut.max_cut_value(x, w))
        """
        return result


if __name__ == "__main__":
    unittest.main()
