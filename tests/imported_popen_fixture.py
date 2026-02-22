from subprocess import Popen as imported_popen
import subprocess


def run_imported_popen(cmdline):
    return imported_popen(cmdline, stdout=subprocess.PIPE)
