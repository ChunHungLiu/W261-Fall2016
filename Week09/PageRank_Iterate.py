from __future__ import division
from mrjob.job import MRJob
from mrjob.step import MRStep
from mrjob.protocol import JSONProtocol

class iterate(MRJob):

    #------------------
    # Configurations: 
    
    def configure_options(self):
        super(iterate, self).configure_options()
        self.add_passthrough_option('--numNodes', default=1, type='int')
        self.add_passthrough_option('--alpha', default=0.85, type='float')
        self.add_passthrough_option('--iterations', default=1, type='int')
    
    INPUT_PROTOCOL = JSONProtocol
    
    #------------------
    # Mapper:
    # - Find the number of neighbors for the node
    # - Distribute current PageRank among all neighbors
    # - If there are no neighbors, keep track of dangling mass
    
    def mapper_dist(self, key, value):

        # Divide the current PageRank by the number of neighbors
        
        numNeighbors = len(value[0])
        PageRank = value[1]
        
        # If there are neighbors, distribute the PageRank to each neighbors
        
        if numNeighbors > 0:
            for neighbor in value[0]:
                yield neighbor, PageRank / numNeighbors
                
        # If there are no neighbors, we need to account for this dangling node
        
        else:
            yield '*dangling', PageRank
        
        # Maintain the graph structure
        
        yield key, value[0]
     
    #------------------
    # Reducer:
    # - For each node, accumulate PageRank distributed from other nodes
    # - Maintain graph structure
    
    def reducer_dist(self, key, values):
        
        new_PageRank = 0.0
        neighbors = {}
        
        for val in values:
            if type(val) == type(0.0):
                new_PageRank += val
            elif type(val) == type({}):
                neighbors = val

        yield key, (neighbors, new_PageRank)

    #------------------
    # Mapper: 
    # - Account for teleportation
    # - Distribute dangling mass to all nodes
    
    # Below is doing it with only one reducer
    # This isn't a good way to do it, but couldn't figure out a better way
    
    def mapper_dangle(self, key, value):
        yield key, value
        
    def reducer_init(self):
        self.m = 0.0
        
    def reducer_dangle(self, key, values):
        
        PageRank = 0
        neighbors = {}
        
        for val in values:
            PageRank = val[1]
            neighbors = val[0]
            
        if key == '*dangling':
            self.m = PageRank
        else:
            a = self.options.alpha
            n = self.options.numNodes
            new_PageRank = (1 - a) / n + a * (self.m / n + PageRank)
            yield key, (neighbors, new_PageRank)
            
    #------------------
    # Pipeline:
    
    def steps(self):
        return ([
            MRStep(mapper=self.mapper_dist,
                   reducer=self.reducer_dist),
            MRStep(mapper=self.mapper_dangle,
                   reducer_init=self.reducer_init,
                   reducer=self.reducer_dangle,
                   jobconf={'mapred.reduce.tasks': 1})
            ] * self.options.iterations)

if __name__ == '__main__':
    iterate.run()