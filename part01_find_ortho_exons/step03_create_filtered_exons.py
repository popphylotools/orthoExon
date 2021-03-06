#!/usr/bin/env python

import logging
import os
import re
import shutil
from Bio import SeqIO
from Bio.Alphabet import IUPAC
from Bio.SeqRecord import SeqRecord


# define functions to parse coordinates of cds's from concatinated aligned fasta w/ n's and -'s

def findBreakpoints(seq):
    n_count = 50
    breakpoints = []
    loc = 0
    regex = re.compile(r"n+[-+n]*")
    while True:
        # loc = seq.find(nnn, loc)
        match = regex.search(seq, loc)
        if not match:
            break
        if len(match.group().replace('-', '')) >= n_count:
            breakpoints.append(match.span())
        loc = match.end()
    return breakpoints


def findExonCoords(seq):
    breakpoints = findBreakpoints(seq)
    length = len(seq)

    if len(breakpoints) == 0:
        return [(0, length)]

    if len(breakpoints) == 1:
        bp = breakpoints[0]
        return [(0, bp[0]), (bp[1], length)]

    elif len(breakpoints) > 0:
        exonCoords = [(0, breakpoints[0][0])]

        for i in range(len(breakpoints) + 1)[1:-1]:  # all intermediate exons
            ex_start = breakpoints[i - 1][1]
            ex_end = breakpoints[i][0]
            exonCoords.append((ex_start, ex_end))

        exonCoords.append((breakpoints[-1][1], length))  # last exon
        return exonCoords


def gapPercent(seq):
    seq = str(seq)
    gappedLen = len(seq)
    gapCount = seq.count('-')
    return (100.0 * gapCount) / gappedLen


def longestGap(seq):
    seq = str(seq)
    gap_regex = re.compile(r"-+")
    gap_list = gap_regex.findall(seq)
    if gap_list:
        return sorted([len(gap) for gap in gap_list], reverse=True)[0]
    else:
        return 0


def create_filtered_exons(enhanced_alignment_path, fasta_output_path, template_species_list, min_exon_length,
                          max_gap_length, max_gap_percent):
    # create handles for all .fasta files in aligned_full_fasta directory
    aligned_fasta_fn = {name.split('.full')[0]: enhanced_alignment_path + name for name in
                        os.listdir(enhanced_alignment_path) if
                        ((".fasta.aln" in name) and (".fasta.aln.fai" not in name))}

    # read and parse fasta files for each species
    aligned_fasta = {}
    for ortho in aligned_fasta_fn.keys():
        aligned_fasta[ortho] = {seq_record.id: seq_record
                                for seq_record in SeqIO.parse(aligned_fasta_fn[ortho],
                                                              "fasta", alphabet=IUPAC.ambiguous_dna)}

    # parse coords from template species in aligned fasta's and trash entries w/ all gaps
    coords = {}  # coords[ortho][sp] = [coord, ]
    for ortho in aligned_fasta:
        coords[ortho] = {}
        for sp in template_species_list:
            seq = str(aligned_fasta[ortho][sp].seq)
            temp_coords = findExonCoords(str(aligned_fasta[ortho][sp].seq))
            for start, end in temp_coords:
                cds = seq[start:end]
                if len(cds) != cds.count('-'):
                    if sp not in coords[ortho]:
                        coords[ortho][sp] = (start, end)
                    elif type(coords[ortho][sp]) is list:
                        coords[ortho][sp].append((start, end))
                    else:
                        temp = coords[ortho][sp]
                        coords[ortho][sp] = [temp, (start, end)]

    # sanity check for multiple non gap template cds's per ortho,sp
    for ortho in coords:
        for sp in coords[ortho]:
            if type(coords[ortho][sp]) is list:
                logging.error("problem parsing coords. multiple non-gap template cds's for {},{}: {}".format(ortho, sp,
                                                                                                             coords[
                                                                                                                 ortho][
                                                                                                                 sp]))

    # Filter aligned exons
    ortho_coords = {}
    for ortho in coords:
        ortho_coords[ortho] = {}
        for sp in coords[ortho]:
            coord = coords[ortho][sp]

            # filter for length
            start, end = coord
            length = end - start
            # if not min_exon_length <= length
            if not min_exon_length <= length:
                continue

            # filter for gap percent
            seq = str(aligned_fasta[ortho][sp].seq[start:end])
            if gapPercent(seq) > max_gap_percent:
                continue

            # filter for gap length
            if longestGap(seq) > max_gap_length:
                continue

            # prep to filter for species membership of ortho
            if coord not in ortho_coords[ortho].keys():
                ortho_coords[ortho][coord] = set()
            ortho_coords[ortho][coord].add(sp)

    # set of coords per ortho which were represented in all species
    universal_ortho_coords = {}
    for ortho in ortho_coords:
        for coord in ortho_coords[ortho]:
            sp_set = ortho_coords[ortho][coord]
            if len(sp_set) == len(template_species_list):
                if ortho not in universal_ortho_coords.keys():
                    universal_ortho_coords[ortho] = set()
                universal_ortho_coords[ortho].add(coord)
            else:
                logging.info("2nd alignment broke up {} {}, has only {}. excluding".format(ortho, coord, sp_set))

    # fasta prep
    fasta_prep = {}
    for ortho in universal_ortho_coords:
        fasta_prep[ortho] = []
        for coord in universal_ortho_coords[ortho]:
            temp_sp_list = []
            for sp in sorted(aligned_fasta[ortho]):
                start, end = coord
                seq = aligned_fasta[ortho][sp].seq[start:end]
                des = aligned_fasta[ortho][sp].description
                seqReq = SeqRecord(seq, id=sp, description=des)
                if sp in template_species_list:
                    fasta_prep[ortho].append(seqReq)
                else:
                    temp_sp_list.append(seqReq)

            fasta_prep[ortho].extend(temp_sp_list)

    for ortho in fasta_prep:
        fasta_prep[ortho] = [seqReq for seqReq in fasta_prep[ortho] if
                             (gapPercent(seqReq.seq) <= max_gap_percent) and (
                                 longestGap(seqReq.seq) <= max_gap_length)]

    fasta_prep = {ortho: seq_list for ortho, seq_list in fasta_prep.items() if len(seq_list) >= 8}

    # fasta output
    shutil.rmtree(fasta_output_path, ignore_errors=True)
    os.makedirs(fasta_output_path, exist_ok=True)
    for ortho in fasta_prep:
        filename = fasta_output_path + ortho + ".full.fasta"
        with open(filename, "w") as f:
            for seqReq in fasta_prep[ortho]:
                f.write(seqReq.format("fasta"))


if __name__ == '__main__':
    import argparse
    import pytoml

    parser = argparse.ArgumentParser()
    parser.add_argument('--configPath', help='configPath', default='../config.toml')
    args = parser.parse_args()

    # load config file
    with open(args.configPath) as toml_data:
        config = pytoml.load(toml_data)

    create_filtered_exons(config['enhanced_alignment_path'], config['fasta_output_path'],
                          config['template_species_list'],
                          config['min_exon_length'], config['max_gap_length'], config['max_gap_percent'])
