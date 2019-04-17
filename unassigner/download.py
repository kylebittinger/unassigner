import collections
import os
import subprocess
import tarfile

from unassigner.parse import parse_fasta, parse_greengenes_accessions

LTP_METADATA_COLS = [
    "accession",
    "start",
    "stop",
    "unknown",
    "fullname_ltp",
    "type_ltp",
    "hi_tax_ltp",
    "riskgroup_ltp",
    "url_lpsn_ltp",
    "tax_ltp",
    "rel_ltp",
    "NJ_support_pk4_ltp"
    ]
LTP_METADATA_URL = \
    "https://www.arb-silva.de/fileadmin/silva_databases/living_tree/LTP_release_128/LTPs128_SSU/LTPs128_SSU.csv"
LTP_SEQS_URL = \
    "https://www.arb-silva.de/fileadmin/silva_databases/living_tree/LTP_release_128/LTPs128_SSU/LTPs128_SSU_unaligned.fasta"
GG_SEQS_URL = \
    "ftp://greengenes.microbio.me/greengenes_release/gg_13_5/gg_13_5.fasta.gz"
GG_ACCESSIONS_URL = \
    "ftp://greengenes.microbio.me/greengenes_release/gg_13_5/gg_13_5_accessions.txt.gz"
SPECIES_FASTA_FP = "species.fasta"
REFSEQS_FASTA_FP = "refseqs.fasta"
GG_DUPLICATE_FP = "gg_duplicate_ids.txt"

def clean(db_dir):
    fps = [
        url_fp(LTP_METADATA_URL),
        url_fp(LTP_SEQS_URL),
        SPECIES_FASTA_FP,
        gunzip_fp(url_fp(GG_SEQS_URL)),
        gunzip_fp(url_fp(GG_ACCESSIONS_URL)),
        REFSEQS_FASTA_FP,
        GG_DUPLICATE_FP
        ]
    for fp in fps:
        fp_full = os.path.join(db_dir, fp)
        if os.path.exists(fp_full):
            os.remove(fp_full)


def url_fp(url):
    return url.split('/')[-1]


def gunzip_fp(fp):
    return fp[:-3]


def get_url(url, fp):
    if os.path.exists(fp):
        os.remove(fp)
    subprocess.check_call(["wget", "-O", fp, url])
    return fp


def process_ltp_seqs(input_fp, output_fp=SPECIES_FASTA_FP):
    if os.path.isdir(output_fp):
        output_fp = os.path.join(output_fp, SPECIES_FASTA_FP)
    # Re-format FASTA file
    with open(input_fp) as f_in:
        seqs = parse_fasta(f_in)
        with open(output_fp, "w") as f_out:
            for desc, seq in seqs:
                vals = desc.split("\t")
                accession = vals[0]
                species_name = vals[5]
                f_out.write(
                    ">{0}\t{1}\n{2}\n".format(accession, species_name, seq))
    return output_fp


def process_greengenes_seqs(seqs_fp, accessions_fp, output_fp=REFSEQS_FASTA_FP):
    duplicates_fp = GG_DUPLICATE_FP
    if os.path.isdir(output_fp):
        duplicates_fp = os.path.join(output_fp, duplicates_fp)
        output_fp = os.path.join(output_fp, REFSEQS_FASTA_FP)

    # Extract table of accessions
    if accessions_fp.endswith(".gz"):
        subprocess.check_call(["gunzip", "-f", accessions_fp])
        accessions_fp = gunzip_fp(accessions_fp)

    # Load accessions
    gg_accessions = {}
    with open(accessions_fp) as f:
        for ggid, src, acc in parse_greengenes_accessions(f):
            gg_accessions[ggid] = (acc, src)

    # Extract FASTA file
    if seqs_fp.endswith(".gz"):
        subprocess.check_call(["gunzip", "-f", seqs_fp])
        seqs_fp = gunzip_fp(seqs_fp)

    # Remove duplicate reference seqs
    uniq_seqs = collections.defaultdict(list)
    with open(seqs_fp) as f:
        for ggid, seq in parse_fasta(f):
            uniq_seqs[seq].append(ggid)

    with open(duplicates_fp, "w") as dups:
        with open(output_fp, "w") as f:
            for seq, ggids in uniq_seqs.items():
                ggid = ggids[0]
                if len(ggids) > 1:
                    dups.write(" ".join(ggids))
                # Re-label seqs with accession numbers
                acc, src = gg_accessions[ggid]
                f.write(">%s %s %s\n%s\n" % (acc, src, ggid, seq))

    return output_fp