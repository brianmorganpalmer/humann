#!/usr/bin/env python

from __future__ import print_function # Python 2.7+ required
import sys
import csv
import argparse
import util

# ---------------------------------------------------------------
# constants
# ---------------------------------------------------------------

c_levels = [
    "Kingdom",
    "Phylum",
    "Class",
    "Order",
    "Family",
    "Genus",
]
c_tmode = "totals"
c_umode = "unclassified"
c_smode = "stratified"
c_tol_header = "# TOL"
c_lca_header = "# LCA"

# ---------------------------------------------------------------
# helper objects
# ---------------------------------------------------------------

class Taxon:
    def __init__( self, name, rank, parent_name ):
        self.name = name
        self.rank = rank
        self.parent_name = parent_name

class TreeOfLife:
    def __init__( self ):
        self.nodes = {}
        self.root = Taxon( "ROOT", "ROOT", None )
        self.nodes[self.root.name] = self.root
    def attach( self, node ):
        if node.name not in self.nodes:
            self.nodes[node.name] = node
        else:
            print( "Taxon <{}> already defined".format( node.name ), file=sys.stderr )
    def get_lineage( self, name ):
        lineage = []
        while name in self.nodes and name != self.root.name:
            node = self.nodes[name]
            lineage.append( [node.rank, node.name] )
            name = node.parent_name
        lineage.append( [self.root.rank, self.root.name] )
        return lineage

# ---------------------------------------------------------------
# argument parsing
# ---------------------------------------------------------------

def get_args( ):
    parser = argparse.ArgumentParser()
    parser.add_argument( "-i", "--input", 
                         required=True,
                         help="HUMAnN2 output table" )
    parser.add_argument( "-o", "--output", 
                         default=None,
                         help="Destination for modified table" )
    parser.add_argument( "-l", "--level",
                         choices=c_levels,
                         default="Family",
                         help="Desired level for taxonomic estimation/summation" )
    parser.add_argument( "-d", "--datafile", 
                         default="uniref50-tol-lca.dat.gz", 
                         help="Location of the uniref(50/90)-tol-lca data file" )
    parser.add_argument( "-m", "--mode", 
                         choices=[c_tmode, c_umode, c_smode],
                         default=c_tmode,
                         help="Which rows to include in the estimation/summation" )
    parser.add_argument( "-t", "--threshold", 
                         type=float, 
                         default=0, 
                         help="Minimum frequency for a new taxon to be included" )
    args = parser.parse_args()
    return args

# ---------------------------------------------------------------
# utilities
# ---------------------------------------------------------------

def build_taxmap( features, target_rank, p_datafile ):
    unirefs = {k.split( util.c_strat_delim )[0] for k in features}
    unirefs = {k.split( util.c_name_delim )[0] for k in unirefs}
    unirefs = {k for k in unirefs if "UniRef" in k}
    # load tree of life, subset uniref lca annotation and add to taxmap
    tol = TreeOfLife()
    taxmap = {}
    tol_mode = False
    lca_mode = False
    with util.try_zip_open( p_datafile ) as fh:
        for row in csv.reader( fh, csv.excel_tab ):
            if row[0] == c_tol_header:
                print( "Loading tree of life from: {}".format( p_datafile ), file=sys.stderr )
                tol_mode = True
                continue
            if row[0] == c_lca_header:
                print( "Loading UniRef LCAs from: {}".format( p_datafile ), file=sys.stderr )
                tol_mode = False
                lca_mode = True
                continue
            if tol_mode:
                name, rank, parent_name = row
                tol.attach( Taxon( name, rank, parent_name ) )
            elif lca_mode:
                uni, lca = row
                if uni in unirefs:
                    for rank, name in tol.get_lineage( lca ):
                        if rank == target_rank:
                            taxmap[uni] = rank.lower()[0] + "__" + name
                            break
    # augment taxmap with genus-level lineage information for stratified features
    for feature in features:
        feature, name, stratum = util.fsplit( feature )
        if stratum is not None and "g__" in stratum:
            genus = stratum.split( util.c_taxon_delim )[0]
            if target_rank == "Genus":
                taxmap[stratum] = genus
            else:
                genus = genus.replace( "g__", "" )
                for rank, name in tol.get_lineage( genus ):
                    if rank == target_rank:
                        taxmap[stratum] = rank.lower()[0] + "__" + name
                        break
    return taxmap

def tax_connect( feature, taxmap ):
    old = feature
    feature, name, stratum = util.fsplit( feature )
    if stratum is None or stratum == "unclassified":
        stratum2 = taxmap.get( feature, "unclassified" )
    else:
        stratum2 = taxmap.get( stratum, "unclassified" )
    return util.fjoin( feature, name, stratum2 )

# ---------------------------------------------------------------
# main
# ---------------------------------------------------------------

def main( ):
    args = get_args( )
    tbl = util.Table( args.input )
    # build the taxmap
    taxmap = build_taxmap( tbl.rowheads, args.level, args.datafile )
    # refine the taxmap
    counts = {}
    for old, new in taxmap.items():
        counts[new] = counts.get( new, 0 ) + 1
    total = float( sum( counts.values( ) ) )
    count = {k:v/total for k, v in counts.items()}
    taxmap = {old:new for old, new in taxmap.items() if count[new] >= args.threshold}
    # reindex the table
    index = {}
    for i, rowhead in enumerate( tbl.rowheads ):
        feature, name, stratum = util.fsplit( rowhead )
        new_rowhead = tax_connect( rowhead, taxmap )
        # outside of unclassfied mode, keep totals
        if stratum is None and args.mode != c_umode:
            index.setdefault( rowhead, [] ).append( i )
            # in totals mode, guess at taxnomy from uniref name
            if args.mode == c_tmode:
                index.setdefault( new_rowhead, [] ).append( i )
        elif stratum == "unclassified" and args.mode == c_umode:
            # in unclassified mode, make a new row for the total...
            index.setdefault( util.fjoin( feature, name, None ), [] ).append( i )
            # ...then replace "unclassified" with inferred taxonomy
            index.setdefault( new_rowhead, [] ).append( i )
        elif stratum is not None and args.mode == c_smode:
            index.setdefault( new_rowhead, [] ).append( i )
    # rebuild the table
    rowheads2, data2 = [], []
    for rowhead in util.fsort( index ):
        rowheads2.append( rowhead )
        newrow = [0 for k in tbl.colheads]
        for i in index[rowhead]:
            oldrow = map( float, tbl.data[i] )
            newrow = [a + b for a, b in zip( newrow, oldrow )]
        data2.append( newrow )
    tbl.rowheads = rowheads2
    tbl.data = data2
    # output
    tbl.write( args.output, unfloat=True )

if __name__ == "__main__":
    main( )
