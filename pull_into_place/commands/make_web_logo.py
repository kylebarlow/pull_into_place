#!/usr/bin/env python2

"""\
Create a web logos for sequences generated by the design pipeline.

Usage:
    pull_into_place make_web_logo <workspace> <round> <pdf_output>

It would be nice to pass all unparsed options through to weblogo.  I'll have to 
think a bit about how to do that.
"""

from klab import docopt, scripting
from .. import pipeline, structures

import weblogolib as weblogo
import corebio

@scripting.catch_and_print_errors()
def main():
    args = docopt.docopt(__doc__)
    root = args['<workspace>']
    round = args['<round>']
    output_path = args['<pdf_output>']

    # Right now I'm looking at validated designs by default, but the user may 
    # be interested in fixbb designs or restrained models as well.

    workspace = pipeline.ValidatedDesigns(root, round)
    workspace.check_paths()

    designs = [structures.Design(x) for x in workspace.output_subdirs]
    sequences = corebio.seq.SeqList(
            [corebio.seq.Seq(x.resfile_sequence) for x in designs],
            alphabet=corebio.seq.unambiguous_protein_alphabet,
    )

    logo_data = weblogo.LogoData.from_seqs(sequences)
    logo_options = weblogo.LogoOptions()
    logo_options.title = workspace.focus_dir
    logo_format = weblogo.LogoFormat(logo_data, logo_options)

    with open(output_path, 'wb') as logo_file:
        document = weblogo.pdf_formatter(logo_data, logo_format)
        logo_file.write(document)

