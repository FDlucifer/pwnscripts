from os import path, system
from pwnscripts.string_checks import *
from typing import Dict
# Helpfully taken from the one_gadget README.md
import subprocess
def one_gadget(filename):
    return list(map(int, subprocess.check_output(['one_gadget', '--raw', filename]).split(b' ')))

def libc_find(db_dir: str, leaks: Dict[str,int]):
    '''identify a libc id from a `dict` of leaked addresses.
    the `dict` should have key-pairs of func_name:addr
    Will raise IndexError if a single libc id is not isolated.'''
    
    args = [_ for t in [(k,hex(v)) for k,v in leaks.items()] for _ in t]
    found = subprocess.check_output([path.join(db_dir, 'find'), *args]).strip().split(b'\n')
    
    if len(found) == 1: # if a single libc was isolated
        libcid = found[0].split(b'(')[-1][:-1]  # NOTE: assuming ./find output format is "<url> (<id>)". This behavior has changed in the past.
        log.info(b'found libc! id: ' + libcid)
        db = libc_db(db_dir, libcid.decode('utf-8'))
        # Also help to calculate self.base
        a_func, an_addr = list(leaks.items())[0]
        db.calc_base(a_func, an_addr)
        return db
    raise IndexError("incorrect number of libcs identified: %d" % len(found))

class libc_db():
    def __init__(self, db_dir:str, identifier: str):
        self.libpath = path.join(db_dir, 'db', identifier)
        self.__dict__.update({k: v for k, v in locals().items() if k != 'self'}) #magic

        # load up all library symbols
        with open(self.libpath+'.symbols') as f:
            self.symbols = dict(l.split() for l in f.readlines())
        for k in self.symbols: self.symbols[k] = int(self.symbols[k],16)
        
        # load up one_gadget offsets in advance
        if system('which one_gadget > /dev/null'):
            log.info('one_gadget does not appear to exist in PATH. ignoring.')
            self.one_gadget = None
        else:
            self.one_gadget = one_gadget(self.libpath+'.so')

    def calc_base(self, symbol: str, addr: int):
        '''Given the ASLR address of a libc function,
        calculate (and return) the randomised base address'''
        
        self.base = addr - self.symbols[symbol]
        assert is_base_address(self.base)   # check that base addr is reasonable
        return self.base

    def select_gadget(self):
        '''An interactive function to choose a preferred
        one_gadget requirement mid-exploit.'''

        assert self.one_gadget is not None
        system("one_gadget '" + self.libpath+".so'")
        #TODO: find a way to do this that looks less hacky
        option = int(input('choose the gadget to use (0-indexed): '))
        assert 0 <= option < len(self.one_gadget)
        return self.one_gadget[option]

