#!/usr/bin/env python

import gffutils
import json
import logging
import os
import shutil


def create_parent_groups_json(groups_fn, db_path, json_path, template_species_list):
    # create handles for all .db files in intermediate directory
    gff = {name.split('.gff.db')[0]: name for name in os.listdir(db_path) if ".gff.db" in name}
    gff = {key: gffutils.FeatureDB(db_path + value) for key, value in gff.items()}

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
        logging.info("processing {}".format(sp))
        for cds in gff[sp].features_of_type(featuretype='CDS', order_by='start'):
            if sp in template_species_list:
                acc = cds.attributes['Name'][0]
            else:
                acc = cds['Parent'][0].split('|')[-1].strip()
            if acc in acc_of_interest[sp]:
                acc_of_interest[sp].remove(acc)
                ortho = acc_ortho_dict[sp][acc]
                if ortho not in parent_groups:
                    parent_groups[ortho] = {}
                parents = [p for p in gff[sp].parents(cds, level=1)]
                if len(parents) is not 1:
                    logging.error(
                        "problem finding parents of cds. sp: {} cds: {}\tparents: {}".format(sp, cds, parents))
                parent_groups[ortho][sp] = parents[0].id

    # output parent_groups to groups.json
    filename = json_path + "groups.json"
    os.makedirs(json_path, exist_ok=True)
    shutil.rmtree(filename, ignore_errors=True)
    with open(filename, 'w') as f:
        json.dump(parent_groups, f)


if __name__ == '__main__':
    import argparse
    import pytoml

    parser = argparse.ArgumentParser()
    parser.add_argument('--configPath', help='configPath', default='../config.toml')
    args = parser.parse_args()

    # load config file
    with open(args.configPath) as toml_data:
        config = pytoml.load(toml_data)

    create_parent_groups_json(config['groups_fn'], config['db_path'], config['json_path'],
                              config['template_species_list'])
