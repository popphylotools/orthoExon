#!/usr/bin/env python

import os
import gffutils
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.Alphabet import IUPAC
import json
from pyfaidx import Fasta

# globals
species_list = ["Bcur", "Bdor", "Bole", "Ccap"]
fasta_path = "../input/fasta/"
groups_fn = "../input/groups_filtered_6181genes.txt"
output_path = "../intermediate/4spp_alignment/input/"
db_path = "../intermediate/gff_databases/"
json_path = "../intermediate/json/"

# create handles for all .db files in intermediate directory
gff = {name.split('.gff.db')[0]: name for name in os.listdir(db_path) if ".gff.db" in name}
gff = {key: gffutils.FeatureDB(db_path + value) for key, value in gff.items()}

# create handles for all .fasta files in fasta directory
fasta = {name.split('.nt.fasta')[0]: name for name in os.listdir(fasta_path) if
         ((".nt.fasta" in name) and (".nt.fasta.fai" not in name))}
fasta = {key: Fasta(fasta_path + value) for key, value in fasta.items()}

# import ortholog groups
with open(json_path + "groups.json", 'r') as f:
    parent_groups = json.load(f)

# concatinate cds's for each species,ortho and output a fasta for each ortho
nnn = Seq("nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn", IUPAC.ambiguous_dna)
for ortho in parent_groups:
    with open(output_path + ortho + ".fasta", "w") as f:
        for sp in species_list:
            parent = gff[sp][parent_groups[ortho][sp]]
            strand = parent.strand
            cds_list = gff[sp].children(parent, featuretype="CDS", order_by="start")
            cat_seq = Seq("", IUPAC.ambiguous_dna)
            for i, cds in enumerate(cds_list):
                if i > 0:
                    cat_seq += nnn
                cat_seq += Seq(str(cds.sequence(fasta=fasta[sp], use_strand=False)), IUPAC.ambiguous_dna)
            if strand == '-':
                cat_seq = cat_seq.reverse_complement()
            seqReq = SeqRecord(cat_seq, id=sp, description=parent.id)
            f.write(seqReq.format("fasta"))