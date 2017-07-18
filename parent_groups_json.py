#!/usr/bin/env python

import os
import gffutils
import json

# globals
intermediate_path = "./intermediate/"
groups_fn = "./input/groups_filtered_6181genes.txt"

# create handles for all .db files in intermediate directory
gff = {name.split('.gff.db')[0]: name for name in os.listdir(intermediate_path) if ".gff.db" in name}
gff = {key: gffutils.FeatureDB(intermediate_path + value) for key, value in gff.items()}

# import ortholog groups
with open(groups_fn, 'r') as f:
    groups_raw = f.readlines()
    groups_raw = [line.strip() for line in groups_raw]

# parse ortholog groups
groups = dict()
for line in groups_raw:
    ortho, data = line.split(':')
    ortho = ortho.strip()
    data = data.strip().split()
    data = {elem.split("|")[0]: elem.split("|")[1] for elem in data}
    groups[ortho] = data

# from ortholog groups, create set of acc and dict to get ortho using acc
acc_of_interest = {}
acc_ortho_dict = {}
for ortho in groups.keys():
    for sp in groups[ortho].keys():
        if sp not in acc_of_interest:
            acc_of_interest[sp] = set()
            acc_ortho_dict[sp] = {}
        acc = groups[ortho][sp]
        acc_of_interest[sp].add(acc)
        acc_ortho_dict[sp][acc] = ortho

# find all cds of interest for each ortho and species
parent_groups = {}
for sp in gff:
    print(sp)
    for cds in gff[sp].features_of_type(featuretype='CDS', order_by='start'):
        if sp in ["Bcur", "Bdor", "Bole", "Ccap"]:
            acc = cds.attributes['Name'][0]
        else:
            acc = cds['Parent'][0].split('|')[-1].strip()
        if acc in acc_of_interest[sp]:
            acc_of_interest[sp].remove(acc)
            ortho = acc_ortho_dict[sp][acc]
            if ortho not in parent_groups:
                parent_groups[ortho] = {}
            parents = [parent for parent in gff[sp].parents(cds) if parent.featuretype in ["mRNA", "prediction"]]
            if len(parents) is not 1:
                print("error in cds: {}\nparents: {}".format(cds, parents))
            parent_groups[ortho][sp] = parents[0].id

# output parent_groups to groups.json
with open(intermediate_path + "groups.json", 'w') as f:
    json.dump(parent_groups, f)