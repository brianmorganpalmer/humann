"""
Stores the alignments identified
Stores the genes/reactions from the database selected
Stores the reactions/pathways from the database selected
Stores the pathways identified
Stores the unaligned reads
"""
import os, re
import config, utilities

class alignments:
    """
    Holds all of the alignments for all bugs
    """
    
    def __init__(self):
        self.hits=[]
        self.bugs={}
        self.genes={}
        
    def add(self, reference, query, evalue, bug): 
        """ 
        Add the hit to the list
        Add the index of the hit to the bugs list and gene list
        """
        
        self.hits.append([bug, reference, query, evalue]) 
        
        index=len(self.hits)-1
        if bug in self.bugs:
            self.bugs[bug].append(index)
        else:
            self.bugs[bug]=[index]
            
        if reference in self.genes:
            self.genes[reference].append(index)
        else:
            self.genes[reference]=[index]
            
    def count_bugs(self):
        """ 
        Return total number of bugs
        """
        return len(self.bugs.keys())
    
    def count_genes(self):
        """ 
        Return total number of genes
        """
        return len(self.genes.keys())    
            
    def print_bugs(self):
        """
        Print out the bugs and total number of hits
        """
        for bug in self.bugs.keys():
            print bug + ": " + str(len(self.bugs[bug])) + " hits"
            
    def gene_list(self):
        """
        Return a list of all of the gene families
        """
        
        return self.genes.keys()
    
    def bug_list(self):
        """
        Return a list of all of the bugs
        """
        
        return self.bugs.keys()
    
    def hits_for_gene(self,gene):
        """
        Return the alignments for the selected gene
        """
        
        hit_list=[]        
        for index in self.genes[gene]:
            hit_list.append(self.hits[index])
            
        return hit_list
    
    def hits_for_bug(self,bug):
        """
        Return the alignments for the selected bug
        """
        hit_list=[]        
        for index in self.bugs[bug]:
            hit_list.append(self.hits[index])
            
        return hit_list
    
    def delete_gene_and_hits(self,gene):
        """
        Remove the gene and all data for all hits associated with the gene
        """
        
        if gene in self.genes:
            for index in self.genes[gene]:
                # Remove the data for the hit
                self.hits[index]=[]
            # Remove the gene entry
            del self.genes[gene]
            
    def update_hits_for_bugs(self):
        """
        Update the hit indexes associated with all of the bugs to remove
        any indexes that point to deleted hits
        """
        
        for bug in self.bugs:
            updated_indexes=[]
            for index in self.bugs[bug]:
                # Check if the hit is empty
                if self.hits[index]:
                    updated_indexes.append(index)
            self.bugs[bug]=updated_indexes
                    
    
class pathways_and_reactions:
    """
    Holds all of the pathways and reaction scores for one bug
    """
    
    def __init__(self, bug):
        self.pathways={}
        self.bug=bug
        
    def add(self, reaction, pathway, score): 
        """ 
        Add the pathway data to the dictionary
        """
        
        if pathway in self.pathways:
            self.pathways[pathway][reaction]=score
        else:
            self.pathways[pathway]={ reaction : score }
    
    def get_bug(self):
        """
        Return the bug associated with the pathways data
        """
        
        return self.bug
    
    def get_items(self):
        """
        Return the items in the pathways dictionary
        """
        
        return self.pathways.items()
    
    def median_score(self):
        """
        Compute the median score for all scores in all pathways
        """
        
        # Create a list of all of the scores in all pathways
        all_scores=[]
        for item in self.pathways.values():
            all_scores+=item.values()
        
        all_scores.sort()
        
        # Find the median score value
        median_score_value=0
        if all_scores:
            if len(all_scores) % 2 == 0:
                index1=len(all_scores)/2
                index2=index1-1
                median_score_value=(all_scores[index1]+all_scores[index2])/2.0
            else:
                median_score_value=all_scores[len(all_scores)/2]
            
        return median_score_value
    
class pathways:
    """
    Holds the pathways coverage or abundance data for a bug
    """
    
    def __init__(self, bug="None", pathways={}):
        self.bug=bug
        self.pathways=pathways

    def get_bug(self):
        """
        Return the bug associated with the pathways data
        """
        
        return self.bug
    
    def get_score(self, pathway):
        """
        Return the score for the pathway
        If the pathway does does not have a score, return 0
        """
        
        return self.pathways.get(pathway, 0)
    
    def get_items(self):
        """
        Return the items in the pathways dictionary
        """
        
        return self.pathways.items()
        
    
class reactions_database:
    """
    Holds all of the genes/reactions data from the file provided
    """
    
    def __init__(self, database):
        """
        Load in the reactions data from the database
        """
        self.reactions_to_genes={}
        self.genes_to_reactions={}
         
        file_handle=open(database,"r")
         
        line=file_handle.readline()
         
        # database is expected to contain a single line per reaction
        # this line begins with the reaction name and ec number and is followed 
        # by all genes associated with the reaction
         
        while line:
            data=line.rstrip().split(config.reactions_database_delimiter)
            if len(data)>2:
                reaction=data.pop(0)
                ec_number=data.pop(0)
             
                # store the data
                self.reactions_to_genes[reaction]=data
             
                for gene in data:
                    if gene in self.genes_to_reactions:
                        self.genes_to_reactions[gene]+=[reaction]
                    else:
                        self.genes_to_reactions[gene]=[reaction]    
             
            line=file_handle.readline()
        
        file_handle.close()
        
    def find_reactions(self,gene):
        """
        Return the list of reactions associated with the gene
        """
            
        return self.genes_to_reactions.get(gene,[])
    
    def find_genes(self,reaction):
        """
        Return the list of genes associated with the reaction
        """
        
        return self.reactions_to_genes.get(reaction,[])
         
    def reaction_list(self):
        """
        Return the list of all the reactions in the database
        """
           
        return self.reactions_to_genes.keys()
    
    def gene_list(self):
        """
        Return the list of all the genes in the database
        """
           
        return self.genes_to_reactions.keys()
    
    def gene_present(self, gene):
        """
        Check if the gene is included in the database
        """
        
        present=False
        if gene in self.genes_to_reactions:
            present=True
            
        return present
    
class pathways_database:
    """
    Holds all of the reactions/pathways data from the file provided
    """
    
    def is_pathway(self, item):
        """
        Determine if the item is a pathway or reaction
        """
        
        pathway=False
        # identifier can be at the beginning or end of the string
        if re.search("^"+config.pathway_identifier, 
            item) or re.search(config.pathway_identifier+"$", item):
            pathway=True
        
        return pathway    
    
    def return_reactions(self, pathway, reactions):
        """
        Search recursively to find the reactions associated with the given pathway
        """
        
        reactions_for_pathway=[]
        for item in reactions.get(pathway,[]):
            # go through items to look for pathways to resolve
            if self.is_pathway(item):
                # find the reactions for the pathway
                reactions_for_pathway+=self.return_reactions(item, reactions)
            else:
                reactions_for_pathway+=[item]
                
        return reactions_for_pathway

    def __init__(self, database):
        """
        Load in the pathways data from the database
        """
        self.pathways_to_reactions={}
        self.reactions_to_pathways={}
        
        file_handle=open(database,"r")
         
        line=file_handle.readline()
         
        # database is expected to contain a single line per pathway
        # this line begins with the pathway name and is followed 
        # by all reactions and/or pathways associated with the pathway
         
        reactions={}
        while line:
            data=line.strip().split(config.pathways_database_delimiter)
            if len(data)>1:
                pathway=data.pop(0)
                reactions[pathway]=data
                
            line=file_handle.readline()
        
        file_handle.close()
        
        # process recursive pathways
        for pathway in reactions:
            for item in reactions[pathway]:
                # go through items to look for pathways to resolve
                reaction=[item]
                # identifier can be at the start or the end of the item name
                if self.is_pathway(item):
                    # find the reactions for the pathway
                    reaction=self.return_reactions(item, reactions)
                
                self.pathways_to_reactions[pathway]=self.pathways_to_reactions.get(
                    pathway,[]) + reaction
                    
        # store all pathways associated with a reaction
        for pathway in self.pathways_to_reactions:
            for reaction in self.pathways_to_reactions[pathway]:
                self.reactions_to_pathways[reaction]=self.reactions_to_pathways.get(
                    reaction,[]) + [pathway]
    
    def find_reactions(self,pathway):
        """
        Return the list of reactions associated with the pathway
        """
         
        return self.pathways_to_reactions.get(pathway, [])

    def find_pathways(self,reaction):
        """
        Return the list of pathways associated with the reaction
        """
         
        return self.reactions_to_pathways.get(reaction, [])
    
    def reaction_list(self):
        """
        Return the list of reactions included in the database
        """
        
        return self.reactions_to_pathways.keys()
    
    def pathway_list(self):
        """
        Return the list of pathways included in the database
        """
        
        return self.pathways_to_reactions.keys()
    
    def get_database(self):
        """
        Return the database as a flat file with a single pathway per line
        """
        
        data=[]
        for pathway in self.pathways_to_reactions:
            data.append(pathway+config.pathways_database_delimiter+
                config.pathways_database_delimiter.join(self.pathways_to_reactions[pathway]))
            
        return "\n".join(data)
    
class reads:
    """
    Holds all of the reads data to create a fasta file
    """
    
    def add(self, id, sequence):
        """
        Store the sequence and id which should correspond to the following:
        >id
        sequence
        """
        
        self.reads[id]=sequence
    
    def __init__(self, file=None):
        """
        Create initial data structures and load if file name provided
        """
        self.reads={}
              
        if file:
            
            # Check the file exists and is readable
            utilities.file_exists_readable(file)
            
            # Check that the file of reads is fasta
            # If it is fastq, then convert the file to fasta
            temp_file=""
            if utilities.fasta_or_fastq(file) == "fastq":
                input_fasta=utilities.fastq_to_fasta(file)
                temp_file=input_fasta
            else:
                input_fasta=file
                       
            file_handle=open(input_fasta,"r")
            
            sequence=""
            id=""
            for line in file_handle:
                if re.search("^>", line):
                    # store the prior sequence
                    if id:
                        self.add(id, sequence)
                    id=line.rstrip().replace(">","")
                    sequence=""
                else:
                    sequence+=line.rstrip()
            
            # add the last sequence
            self.add(id, sequence)
                
            file_handle.close()
            
            # Remove the temp fasta file if exists
            if temp_file:
                utilities.remove_file(temp_file)
    
    def remove_id(self, id):
        """
        Remove the id and sequence from the read structure
        """
        
        if id in self.reads:
            del self.reads[id]
                
    def get_fasta(self):
        """ 
        Return a string of the fasta file sequences stored
        """
        
        fasta=[]
        for id, sequence in self.reads.items():
            fasta.append(">"+id+"\n"+sequence)
        
        return "\n".join(fasta)
    
    def id_list(self):
        """
        Return a list of all of the fasta ids
        """
        
        return self.reads.keys()
    