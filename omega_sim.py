import re
import itertools
import sys

class OmegaNetwork:
    def __init__(self, size=8):
        self.size = size
        self.stages = size.bit_length() - 1

    def _shuffle(self, value):
        # Shuffle Function
        ret = ((value << 1) & (self.size - 1)) | (value >> (self.stages - 1))
        return ret

    def get_path_resources(self, src, dst):
        """
        Returns a list of unique resource IDs used by the path from src to dst.
        Resource ID format: (stage_index, switch_index, output_port)
        """
        resources = []
        current_node = src
        
        # Destination binary bits for routing
        # For N=8, bits are d2, d1, d0
        dst_bits = [(dst >> i) & 1 for i in range(self.stages - 1, -1, -1)]
        
        path_trace = [] # Debug info
        
        for stage in range(self.stages):
            input_node = self._shuffle(current_node)
            
            switch_idx = input_node // 2
            
            # Determine Routing
            # Bit 0 -> Upper (0), Bit 1 -> Lower (1)
            target_port = dst_bits[stage]
            
            # Record resource usage
            # Track the specific output port of a specific switch at a specific stage
            resources.append((stage, switch_idx, target_port))
            
            output_node = 2 * switch_idx + target_port
            
            current_node = output_node
            
        return resources

    def check_blocking(self, mapping):
        """
        mapping: dict {input: output}
        Returns: (is_blocking, conflicts)
        conflicts: list of sets of (src, dst) that conflict
        """
        # Map resource -> list of (src, dst) using it
        resource_usage = {}
        
        for src, dst in mapping.items():
            path = self.get_path_resources(src, dst)
            for res in path:
                if res not in resource_usage:
                    resource_usage[res] = []
                resource_usage[res].append((src, dst))
        
        conflicts = []
        is_blocking = False
        for res, users in resource_usage.items():
            if len(users) > 1:
                is_blocking = True
                conflicts.append(tuple(users))
                
        return is_blocking, conflicts

    def solve_schedule(self, mapping):
        """
        Returns a list of cycles, where each cycle is a list of (src, dst) pairs
        that can be transmitted simultaneously.
        Uses graph coloring on the conflict graph.
        """
        connections = list(mapping.items())
        n = len(connections)
        
        # Build adjacency matrix of conflicts
        adj = [[False] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(i + 1, n):
                src1, dst1 = connections[i]
                src2, dst2 = connections[j]
                
                path1 = set(self.get_path_resources(src1, dst1))
                path2 = set(self.get_path_resources(src2, dst2))
                
                # If intersection is not empty, they conflict
                if not path1.isdisjoint(path2):
                    adj[i][j] = adj[j][i] = True
        
        # Graph coloring
        # Simple greedy or backtracking. For N=8, we want optimal (min colors).
        # Try to color with k=1, 2, ... until valid.
        
        def is_valid(coloring, k_colors):
            for i in range(n):
                for j in range(i + 1, n):
                    if adj[i][j] and coloring[i] == coloring[j]:
                        return False
            return True

        def solve_coloring(idx, coloring, k_colors):
            if idx == n:
                return True
            
            for c in range(k_colors):
                # Check if color c is valid for node idx
                valid_color = True
                for neighbor in range(idx):
                    if adj[idx][neighbor] and coloring[neighbor] == c:
                        valid_color = False
                        break
                
                if valid_color:
                    coloring[idx] = c
                    if solve_coloring(idx + 1, coloring, k_colors):
                        return True
                    coloring[idx] = -1
            return False

        # Try increasing number of cycles
        for k in range(1, n + 1):
            coloring = [-1] * n
            if solve_coloring(0, coloring, k):
                # Reconstruct schedule
                schedule = [[] for _ in range(k)]
                for idx, color in enumerate(coloring):
                    schedule[color].append(connections[idx])
                return schedule
        
        return [connections] # Should not happen

    def get_switch_states(self, connections):
        """
        Determines the state of switches for a set of connections.
        connections: list of (src, dst)
        Returns: list of lists (one per stage) of dictionary {switch_idx: state}
                 State: 'Straight' or 'Cross'
        """
        # Initialize states for all switches as None (or Unused)
        # stages[stage_idx][switch_idx]
        switch_states = [[None] * (self.size // 2) for _ in range(self.stages)]
        
        for src, dst in connections:
            current_node = src
            dst_bits = [(dst >> i) & 1 for i in range(self.stages - 1, -1, -1)]
            
            for stage in range(self.stages):
                input_node = self._shuffle(current_node)
                switch_idx = input_node // 2
                in_port = input_node % 2
                
                target_port = dst_bits[stage]
                
                # Determine state: 0 (Straight) if in==out, 1 (Cross) if in!=out
                state_code = in_port ^ target_port
                state_str = "Cross" if state_code else "Straight"
                
                # In a valid non-blocking schedule, if the switch is already set, 
                # it must be consistent. We assume the schedule is valid here.
                switch_states[stage][switch_idx] = state_str
                
                output_node = 2 * switch_idx + target_port
                current_node = output_node
                
        return switch_states

def parse_cycle_notation(text, n=8):
    """
    Parses string like "(7 0 6 5 2) (4 3) (1)" into a dict {0:?, ... 7:?}
    """
    mapping = {}
    
    # Find all groups in parentheses
    cycles = re.findall(r'\(([\d\s]+)\)', text)
    
    covered = set()
    
    for cycle_str in cycles:
        # Split by whitespace
        nodes = [int(x) for x in cycle_str.strip().split()]
        if not nodes:
            continue
            
        # a -> b -> c -> ... -> a
        for i in range(len(nodes)):
            src = nodes[i]
            dst = nodes[(i + 1) % len(nodes)]
            mapping[src] = dst
            covered.add(src)
            
    # Handle missing nodes (fixed points) if any, though the input usually specifies all or implies fixed?
    # Usually in cycle notation, missing elements map to themselves.
    for i in range(n):
        if i not in covered:
            mapping[i] = i
            
    return mapping

def print_schedule(schedule, sim):
    for i, cycle in enumerate(schedule):
        print(f"  Cycle {i+1}:")
        items = [f"{src}->{dst}" for src, dst in cycle]
        print(f"    Transmissions: {', '.join(items)}")
        
        states = sim.get_switch_states(cycle)
        print("    Switch Settings:")
        for stage_idx, stage_states in enumerate(states):
            settings = []
            for sw_idx, state in enumerate(stage_states):
                val = state if state else "Unused"
                # Abbreviate for compactness
                v_short = "0" if val == "Straight" else ("1" if val == "Cross" else "-")
                settings.append(f"SW{sw_idx}:{v_short}")
            print(f"      Stage {stage_idx}: {'  '.join(settings)}")

def main():
    sim = OmegaNetwork(size=8)
    
    if len(sys.argv) > 1:
        permutations = []
        for i, arg in enumerate(sys.argv[1:]):
            permutations.append((arg, f"Custom Arg {i+1}"))
    else:
        permutations = [
            ("(7 0 6 5 2) (4 3) (1)", "pi1"),
            ("(1 7) (0 3) (4 2) (5 6)", "pi2"),
            ("(6 5 1 2) (0 3 4 7)", "pi3"),
            ("(2 5 3 7 0 4) (1 6)", "pi4"),
            ("(1 2 4 7 6 0 5 3)", "pi5")
        ]
    
    for p_str, name in permutations:
        print(f"--- Analysis for {name} ---")
        print(f"Permutation: {p_str}")
        mapping = parse_cycle_notation(p_str)
        
        # Sort for display stability
        sorted_map = dict(sorted(mapping.items()))
        # print(f"Mapping: {sorted_map}")
        
        is_blocking, conflicts = sim.check_blocking(mapping)
        
        if is_blocking:
            print("Status: BLOCKING")
            # print(f"Conflicts detected: {len(conflicts)} collision points.")
            
            schedule = sim.solve_schedule(mapping)
            print(f"Minimum Cycles: {len(schedule)}")
            print_schedule(schedule, sim)
        else:
            print("Status: NON-BLOCKING")
            print("Minimum Cycles: 1")
            print_schedule([list(mapping.items())], sim)
        
        print()

if __name__ == "__main__":
    print("Scheduling Scheme (0=Straight, 1=Cross, -=Unused):")
    main()
