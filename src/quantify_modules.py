""" 
HUMAnN2: quantify_modules module
Generate pathway coverage and abundance

Copyright (c) 2014 Harvard School of Public Health

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import os
import shutil
import math
import re
import sys
import subprocess
import logging

import utilities
import config
import store
import MinPath12hmp
import quantify_families

# name global logging instance
logger=logging.getLogger(__name__)

def run_minpath(reactions_file,metacyc_datafile):
    """
    Run minpath on the reactions file using the datafile of pathways
    """
    
    # Create temp files for the results
    tmpfile=utilities.unnamed_temp_file()
    
    # Bypass minpath run if reactions file is empty
    if os.path.getsize(reactions_file):
    
        tmpfile2=utilities.unnamed_temp_file()

        # Redirect stdout
        sys.stdout=open(os.devnull,"w")
    
        # Call minpath to identify pathways
        MinPath12hmp.Orth2Path(infile = reactions_file, reportfile = "/dev/null", 
            detailfile = tmpfile, whichdb = "ANY", mapfile=metacyc_datafile,
            mpsfile = tmpfile2)
    
        # Undo stdout redirect
        sys.stdout=sys.__stdout__
    
    return tmpfile


def identify_reactions_and_pathways_by_bug(args):
    """
    Identify the reactions from the hits found for a specific bug
    """
    
    reactions_database, pathways_database, gene_scores, bug = args
    
    # Merge the gene scores to reaction scores   
    message="Compute reaction scores for bug: " + bug
    logger.info(message)
    
    reactions={}
    reactions_file_lines=[]
    for reaction in reactions_database.reaction_list():
        genes_list=reactions_database.find_genes(reaction)
        abundance=0
        # Add the scores for each gene to the total score for the reaction
        for gene in genes_list:
            abundance+=gene_scores.get(gene,0)  
        
        # Only write out reactions where the abundance is greater than 0
        if abundance>0: 
            reactions_file_lines.append(reaction+config.output_file_column_delimiter
                +str(abundance)+"\n")
            # Store the abundance data to compile with the minpath pathways
            reactions[reaction]=abundance

    pathways={}
    # Run minpath if toggle on and also if there is more than one reaction   
    if config.minpath_toggle == "on" and len(reactions_file_lines)>3:   

        # Create a temp file for the reactions results
        reactions_file=utilities.unnamed_temp_file()
        file_handle=open(reactions_file,"w")
        file_handle.write("".join(reactions_file_lines))
        file_handle.close()
 
        # Write a flat reactions to pathways file
        logger.debug("Write flat reactions to pathways file for Minpath")
        pathways_database_file=utilities.unnamed_temp_file()
        file_handle=open(pathways_database_file,"w")
        file_handle.write(pathways_database.get_database())
        file_handle.close()
    
        # Run minpath to identify the pathways
        logger.info("Run MinPath on " + bug)
            
        tmpfile=run_minpath(reactions_file, pathways_database_file)
        
        # Process the minpath results
        if os.path.isfile(tmpfile):

            file_handle_read=open(tmpfile, "r")
            
            line=file_handle_read.readline()
            
            while line:
                data=line.strip().split(config.minpath_pathway_delimiter)
                if re.search(config.minpath_pathway_identifier,line):
                    current_pathway=data[config.minpath_pathway_index]
                else:
                    current_reaction=data[config.minpath_reaction_index]
                    # store the pathway and reaction
                    pathways[current_reaction]=pathways.get(
                        current_reaction,[]) + [current_pathway]      
                line=file_handle_read.readline()
        
            file_handle_read.close()
            
        else:
            message="Empty results file from MinPath run for bug: " + bug
            print(message)
            logger.warning(message)
    else:
        # Add all pathways associated with each reaction if not using minpath
        for current_reaction in reactions:
            pathways[current_reaction]=pathways.get(
                current_reaction, []) + pathways_database.find_pathways(current_reaction) 
     
    pathways_and_reactions_store=store.PathwaysAndReactions(bug)
    
    # Store the pathway abundance for each reaction
    for current_reaction in reactions:
        # Find the pathways associated with reaction
        for current_pathway in pathways.get(current_reaction,[""]):
            # Only store data for items with pathway names
            if current_pathway:
                pathways_and_reactions_store.add(current_reaction, current_pathway, 
                    reactions[current_reaction])
   
    return pathways_and_reactions_store
    
    
def identify_reactions_and_pathways(gene_scores, reactions_database, pathways_database):
    """
    Identify the reactions and then pathways from the hits found
    """
            
    # Set up a command to run through each of the hits by bug
    args=[]
    for bug in gene_scores.bug_list():
        scores=gene_scores.scores_for_bug(bug)
        args.append([reactions_database, pathways_database, scores, bug])
    
    threads=config.threads
    if config.minpath_toggle == "on":
        threads=1
    elif threads>config.max_pathways_threads:
        threads=config.max_pathways_threads
        
    pathways_and_reactions_store=utilities.command_multiprocessing(threads, args, 
        function=identify_reactions_and_pathways_by_bug)

    return pathways_and_reactions_store

def pathways_coverage_by_bug(args):
    """
    Compute the coverage of pathways for one bug
    """
    
    pathways_and_reactions_store, pathways_database = args
    
    logger.debug("Compute pathway coverage for bug: " + pathways_and_reactions_store.get_bug())
    
    # Process through each pathway to compute coverage
    pathways_coverages={}
    xipe_input=[]
    median_score_value=pathways_and_reactions_store.median_score()
    
    for pathway in pathways_and_reactions_store.get_pathways():
            
        reaction_scores=pathways_and_reactions_store.get_reactions(pathway)
        # Count the reactions with scores greater than the median
        count_greater_than_median=0
        for reaction, score in reaction_scores.items():
            if score > median_score_value:
               count_greater_than_median+=1
        
        # Compute coverage
        coverage=0
        total_reactions_for_pathway=len(pathways_database.find_reactions(pathway))
        if total_reactions_for_pathway:
            coverage=count_greater_than_median/float(total_reactions_for_pathway)
        
        pathways_coverages[pathway]=coverage
        xipe_input.append(config.xipe_delimiter.join([pathway,str(coverage)]))
    
    # Check config to determine if xipe should be run
    if config.xipe_toggle == "on":
        # Run xipe
        xipe_exe=os.path.join(os.path.dirname(os.path.realpath(__file__)),
            config.xipe_script)
        
        cmmd=[xipe_exe,"--file2",config.xipe_percent]
        
        message="Run xipe ...."
        logger.info(message)
        if config.verbose:
            print(message)
        xipe_subprocess = subprocess.Popen(cmmd, stdin = subprocess.PIPE,
            stdout = subprocess.PIPE, stderr = subprocess.PIPE )
        xipe_stdout, xipe_stderr = xipe_subprocess.communicate("\n".join(xipe_input))
        
        # Record the pathways to remove based on the xipe error messages
        pathways_to_remove=[]
        for line in xipe_stderr.split("\n"):
            data=line.strip().split(config.xipe_delimiter)
            if len(data) == 2:
                pathways_to_remove.append(data[1])
        
        # Keep some of the pathways to remove based on their xipe scores
        for line in xipe_stdout.split("\n"):
            data=line.strip().split(config.xipe_delimiter)
            if len(data) == 2:
                pathway, pathway_data = data
                if pathway in pathways_to_remove:
                    score, bin = pathway_data[1:-1].split(", ")
                    if float(score) >= config.xipe_probability and int(bin) == config.xipe_bin:
                        pathways_to_remove.remove(pathway)
                
        # Remove the selected pathways
        for pathway in pathways_to_remove:
            del pathways_coverages[pathway]
    
    return store.Pathways(pathways_and_reactions_store.get_bug(), pathways_coverages)

def pathways_abundance_by_bug(args):
    """
    Compute the abundance of pathways for one bug
    """
    
    pathways_and_reactions_store, pathways_database = args
    
    logger.debug("Compute pathway abundance for bug: " + pathways_and_reactions_store.get_bug())

    # Process through each pathway to compute abundance
    pathways_abundances={}
    for pathway in pathways_and_reactions_store.get_pathways():
        
        reaction_scores=pathways_and_reactions_store.get_reactions(pathway)
        # Initialize any reactions in the pathway not found to 0
        for reaction in pathways_database.find_reactions(pathway):
            reaction_scores.setdefault(reaction, 0)
            
        # Sort the scores for all of the reactions in the pathway from low to high
        sorted_reaction_scores=sorted(reaction_scores.values())
            
        # Select the second half of the list of reaction scores
        abundance_set=sorted_reaction_scores[(len(sorted_reaction_scores)/ 2):]
        
        # Compute abundance
        abundance=sum(abundance_set)/len(abundance_set)
        
        pathways_abundances[pathway]=abundance
    
    return store.Pathways(pathways_and_reactions_store.get_bug(), pathways_abundances)
    
    
def print_pathways(pathways, file, header):
    """
    Print the pathways data to a file organized by pathway
    """
    
    logger.debug("Print pathways %s", header)
    
    delimiter=config.output_file_column_delimiter
    category_delimiter=config.output_file_category_delimiter
    
    # Compile data for all bugs by pathways
    all_pathways=store.Pathways()
    all_pathways_scores_by_bug={}
    for bug_pathways in pathways:
        bug=bug_pathways.get_bug()
        # Compile all scores based on score for each bug for each pathway
        if bug == "all":
            all_pathways=bug_pathways
        else:
            for pathway in bug_pathways.get_pathways():
                score=bug_pathways.get_score(pathway)
                if score>0:
                    if not pathway in all_pathways_scores_by_bug:
                        all_pathways_scores_by_bug[pathway]={bug: score}
                    else:
                        all_pathways_scores_by_bug[pathway][bug]=score             
 
    # Create the header
    tsv_output=["# Pathway"+ delimiter + header]       
            
    # Print out the pathways with those with the highest scores first
    for pathway in all_pathways.get_pathways_double_sorted():
        all_score=all_pathways.get_score(pathway)
        if all_score>0:
            # Print the computation of all bugs for pathway
            tsv_output.append(pathway+delimiter+utilities.format_float_to_string(all_score))
            # Process and print per bug if selected
            if not config.remove_stratified_output:
                # Print scores per bug for pathway ordered with those with the highest values first
                if pathway in all_pathways_scores_by_bug:
                    for bug in utilities.double_sort(all_pathways_scores_by_bug[pathway]):
                        tsv_output.append(pathway+category_delimiter+bug+delimiter
                            +utilities.format_float_to_string(all_pathways_scores_by_bug[pathway][bug]))
 
    if config.output_format == "biom":
        # Open a temp file if a conversion to biom is selected
        tmpfile=utilities.unnamed_temp_file()
        file_out=open(tmpfile,"w")
        file_out.write("\n".join(tsv_output))
        file_out.close()
        
        utilities.tsv_to_biom(tmpfile,file,"Pathway")
            
    else:
        # Write the final file as tsv
        file_handle=open(file,"w") 
        file_handle.write("\n".join(tsv_output))                  
        file_handle.close()
    

def compute_pathways_abundance_and_coverage(pathways_and_reactions_store, pathways_database):
    """
    Compute the abundance and coverage of the pathways
    """
    
    threads=config.threads
    if threads>config.max_pathways_threads:
        threads=config.max_pathways_threads
    
    # Compute abundance for all pathways
    args=[]
    for bug_pathway_and_reactions_store in pathways_and_reactions_store:
         args.append([bug_pathway_and_reactions_store, pathways_database])
        
    pathways_abundance=utilities.command_multiprocessing(threads, args, 
        function=pathways_abundance_by_bug)

    # Print the pathways abundance data to file
    print_pathways(pathways_abundance, config.pathabundance_file, "Abundance (reads per kilobase)")

    # Compute coverage
    if config.xipe_toggle == "on":
        threads=1

    pathways_coverage=utilities.command_multiprocessing(threads, args, 
        function=pathways_coverage_by_bug)
    
    # Print the pathways abundance data to file
    print_pathways(pathways_coverage, config.pathcoverage_file, "Coverage")

    return config.pathabundance_file, config.pathcoverage_file
