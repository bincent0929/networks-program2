import atexit
import os
import random
import shutil
import stat
import string
import sys
import tempfile
import pexpect
import filecmp

################### Exception/Error classes ############################
# Base class for all errors
class TestingErrorBase(Exception):
    def __init__(self, message=None):
        super().__init__()
        self.message = message

    def __str__(self):
        if self.message is None:
            return ''

        return self.message

class InternalError(TestingErrorBase):
    def __str__(self):
        msg = 'INTERNAL ERROR: Something unexpected happened, send all files to Dr. Kredo'
        if self.message is not None:
            msg += f': {self.message}'
        return msg

class AbnormalTerminationError(TestingErrorBase):
    pass

class InvalidCommandError(TestingErrorBase):
    pass

class DuplicateCommandError(TestingErrorBase):
    pass

class TestError(TestingErrorBase):
    pass

class EndTestsException(Exception):
    pass

################### JOIN functions ###################################

def student_perform_join(reg, node, peer_id):
    banner('Performing JOIN test')
    student_tx_join(node)
    soln_rx_join(reg, peer_id)

def soln_perform_join(reg, node, peer_id):
    banner('Performing JOIN test')
    (ip, port) = soln_tx_join(node)
    student_rx_join(reg, peer_id)

    return (ip, port)

def student_tx_join(node):
    try:
        tx_join(node)
    except AbnormalTerminationError:
        perror('Program unexpectedly closed during JOIN test.')
        raise

def soln_tx_join(node):
    try:
        tx_join(node)
        ip = None
        port = None
        val = node.expect(
            [
                PREFIX + r'\s+ADDR\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*:\s*(\d+)[^\r]*\r\n',
                pexpect.EOF,
                ERRFIX + r'\s+([^\r]*)\r\n'
            ])
        if val == 0:  # Address and port
            ip = node.match.group(1)
            port = int(node.match.group(2))
        elif val == 1:  # EOF
            raise AbnormalTerminationError()
        elif val == 2:  # Error
            raise TestError(node.match.group(1))
        else:  # Error
            raise InternalError(f'soln_tx_join had expect value {val}.')
    except AbnormalTerminationError as ate:
        raise InternalError('Solution unexpectedly closed during soln_tx_join.') from ate

    if None in (ip, port):
        raise InternalError('Solution did not print ADDR output in soln_tx_join.')

    return (ip, port)

def tx_join(node):
    node.sendline('JOIN')

    verify_alive(node)

def student_rx_join(node, expected_id):
    try:
        rx_id = rx_join(node)
        if rx_id is None:
            perror('Recongizable TEST] JOIN statement not printed.')
            raise EndTestsException()
        if rx_id != expected_id:
            perror(f'ID {rx_id} printed instead of ID {expected_id}.')
            raise EndTestsException()
    except DuplicateCommandError:
        perror('Multiple JOIN responses printed.')
        raise
    except InvalidCommandError as err:
        perror(f'Incorrect response printed: "{err.message}"')
        raise
    except AbnormalTerminationError:
        perror('Program unexpectedly closed during JOIN test.')
        raise
    except UnicodeDecodeError as err:
        perror(f'Program printed non-ASCII characters. {err}')
        raise EndTestsException() from err

def soln_rx_join(node, expected_id):
    try:
        rx_id = rx_join(node)
        if rx_id is None:
            perror('Recognizable JOIN command not sent.')
            raise EndTestsException()
        if rx_id != expected_id:
            perror(f'ID {rx_id} sent instead of ID {expected_id}.')
            raise EndTestsException()
    except DuplicateCommandError:
        perror('Multiple JOIN commands sent.')
        raise
    except InvalidCommandError as err:
        perror(f'Incorrect command sent: "{err.message}"')
        raise
    except AbnormalTerminationError as ate:
        raise InternalError('Solution unexpectedly closed during JOIN test.') from ate
    except UnicodeDecodeError as err:
        raise InternalError(f'Solution printed non-ASCII characters. {err}') from err

def rx_join(node):
    done = False
    rx_id = None
    while not done:
        val = node.expect(
            [
                PREFIX + r'\s+JOIN\s+(\d+)\s*\r\n',
                pexpect.EOF,
                pexpect.TIMEOUT,
                PREFIX + r'\s+(\S*)[^\r]*\r\n',
                ERRFIX + r'\s+([^\r]*)\r\n'
            ])
        if val == 0:  # JOIN with peer ID
            if rx_id is not None:
                raise DuplicateCommandError()
            rx_id = int(node.match.group(1))
        elif val == 1:  # EOF
            raise AbnormalTerminationError()
        elif val == 2:  # TIMEOUT
            done = True
        elif val == 3:  # Incorrect command
            raise InvalidCommandError(" ".join(node.after.split()[1:]))
        elif val == 4:  # Error
            raise TestError(node.match.group(1))
        else:  # Error
            raise InternalError(f'rx_join had expect value {val}.')

    verify_alive(node)

    return rx_id

################### PUBLISH functions ###################################

def student_perform_publish(reg, peer, correct_files):
    banner('Performing PUBLISH test')
    student_tx_publish(peer)
    soln_rx_publish(reg, correct_files)

def soln_perform_publish(reg, peer, correct_files):
    banner('Performing PUBLISH test')
    soln_tx_publish(peer)
    student_rx_publish(reg, correct_files)

def soln_perform_publish_to_soln(reg, peer, correct_files):
    soln_tx_publish(peer)
    try:
        soln_rx_publish(reg, correct_files)
    except TestingErrorBase as err:
        raise InternalError(err.message)

def student_tx_publish(node):
    try:
        tx_publish(node)
    except AbnormalTerminationError:
        perror('Program unexpectedly closed during PUBLISH test.')
        raise

def soln_tx_publish(node):
    try:
        tx_publish(node)
    except AbnormalTerminationError as ate:
        raise InternalError('Solution unexpectedly closed during PUBLISH.') from ate

def tx_publish(node):
    node.sendline('PUBLISH')

    verify_alive(node)

def student_rx_publish(node, correct_files):
    try:
        count, files = rx_publish(node, correct_files)
        if None in (count, files):
            raise TestError('Recognizable TEST] PUBLISH statement not printed.')
    # Just pass TestError
    except DuplicateCommandError:
        perror('Multiple PUBLISH responses printed.')
        raise
    except InvalidCommandError as err:
        perror(f'Incorrect response printed: "{err.message}"')
        raise
    except AbnormalTerminationError:
        perror('Program unexpectedly closed during PUBLISH test.')
        raise
    except UnicodeDecodeError as err:
        perror(f'Program printed non-ASCII characters. {err}')
        raise EndTestsException() from err

def soln_rx_publish(node, correct_files):
    try:
        count, files = rx_publish(node, correct_files)
        if None in (count, files):
            raise TestError('Program did not send recognizable PUBLISH command.')
    # Pass TestError
    except DuplicateCommandError:
        perror('Multiple PUBLISH commands sent.')
        raise
    except InvalidCommandError as err:
        perror(f'Incorrect command sent: "{err.message}"')
        raise
    except AbnormalTerminationError as ate:
        raise InternalError('Solution unexpectedly closed during PUBLISH test.') from ate
    except UnicodeDecodeError as err:
        raise InternalError(f'Solution printed non-ASCII characters. {err}') from err

def rx_publish(node, correct_files):
    done = False
    pub_count = None
    pub_files = None
    while not done:
        val = node.expect(
            [
                PREFIX + r'\s+PUBLISH\s+(\d+)\s+([^\r]*)\r\n',
                pexpect.EOF,
                pexpect.TIMEOUT,
                PREFIX + r'\s+(\S*)[^\r]*\r\n',
                ERRFIX + r'\s+([^\r]*)\r\n'
            ])
        if val == 0:  # PUBLISH with count and filenames
            if pub_count is not None:
                raise DuplicateCommandError()
            pub_count = int(node.match.group(1))
            pub_files = node.match.group(2).split()
            # Verify the file count printed correctly
            if pub_count != len(pub_files):
                raise TestError(f'File count ({pub_count}) does not match number of names ({len(pub_files)}).')
            if pub_count != len(correct_files):
                raise TestError(f'File count equals {pub_count} instead of {len(correct_files)}.')
            # Check the filenames are correct
            if (len(pub_files) != len(correct_files)) \
                    or (len(set(pub_files) - set(correct_files)) != 0) \
                    or (len(set(correct_files) - set(pub_files)) != 0):

                msg = 'Incorrect files.\n'
                msg += f' command files: {", ".join(sorted(pub_files))}\n'
                msg += f' correct files: {", ".join(sorted(correct_files))}'
                raise TestError(msg)
        elif val == 1:  # EOF
            raise AbnormalTerminationError()
        elif val == 2:  # TIMEOUT
            done = True
        elif val == 3:  # Incorrect command
            raise InvalidCommandError(" ".join(node.after.split()[1:]))
        elif val == 4:  # Error
            raise TestError(node.match.group(1))
        else:  # Error
            raise InternalError(f'rx_publish had expect value {val}.')

    verify_alive(node)

    return pub_count, pub_files

################### SEARCH functions ###################################

def student_perform_search(reg, peer, fname, indexed):
    banner(f'Performing SEARCH test for file "{fname}"')
    rx_id, rx_ip, rx_port = student_tx_search(peer, fname)
    rx_fname, correct_id, correct_ip, correct_port = soln_rx_search(reg)

    if (rx_fname, rx_id, rx_ip, rx_port) != (fname, correct_id, correct_ip, correct_port):
        msg = 'SEARCH test had these errors:'
        if rx_fname != fname:
            msg += f'\n Filename "{rx_fname}" sent instead of "{fname}".'

        if (correct_id, correct_ip, correct_port) == (0, '0.0.0.0', 0) \
                and (rx_id, rx_ip, rx_port) != (0, '0.0.0.0', 0):

            msg += f'\n File not indexed, but {rx_id} {rx_ip}:{rx_port} printed.'
        elif (correct_id, correct_ip, correct_port) != (0, '0.0.0.0', 0) \
                and (rx_id, rx_ip, rx_port) == (0, '0.0.0.0', 0):

            msg += f'\n File indexed ({correct_id} {correct_ip}:{correct_port}), but program prints it is not.'
        else:
            if rx_id != correct_id:
                msg += f'\n Peer ID {rx_id} printed instead of {correct_id}'
            if rx_ip != correct_ip:
                msg += f'\n IP {rx_ip} printed instead of {correct_ip}.'
            if rx_port != correct_port:
                msg += f'\n Port {rx_port} printed instead of {correct_port}.'
        raise TestError(msg)

    elif indexed and rx_id == 0:
        msg = 'Client incorrectly states file not indexed at any peer.'
        raise TestError(msg)

def soln_perform_search(reg, peer, fname, correct_id, correct_ip, correct_port):
    banner(f'Performing SEARCH test for file "{fname}"')
    resp_id, resp_ip, resp_port = soln_tx_search(peer, fname)
    rx_fname, rx_id, rx_ip, rx_port = student_rx_search(reg)

    # Check the request info printed at the registry
    if (rx_fname, rx_id, rx_ip, rx_port) != (fname, correct_id, correct_ip, correct_port):
        msg = 'SEARCH test had these errors in request reception at registry:'
        if rx_fname != fname:
            msg += f'\n Filename "{rx_fname}" printed instead of "{fname}".'

        ## Not tested at this time
        if (correct_id, correct_ip, correct_port) == (0, '0.0.0.0', 0) \
                and (rx_id, rx_ip, rx_port) != (0, '0.0.0.0', 0):

            msg += f'\n File should not be indexed, but {rx_id} {rx_ip}:{rx_port} printed.'
        elif (correct_id, correct_ip, correct_port) != (0, '0.0.0.0', 0) \
                and (rx_id, rx_ip, rx_port) == (0, '0.0.0.0', 0):

            msg += f'\n File indexed ({correct_id} {correct_ip}:{correct_port}), but registry prints it is not.'
        else:
            if rx_id != correct_id:
                msg += f'\n Peer ID {rx_id} printed instead of {correct_id}'
            if rx_ip != correct_ip:
                msg += f'\n IP {rx_ip} printed instead of {correct_ip}.'
            if rx_port != correct_port:
                msg += f'\n Port {rx_port} printed instead of {correct_port}.'
        raise TestError(msg)

    # Check the response sent by the registry
    if (resp_id, resp_ip, resp_port) != (correct_id, correct_ip, correct_port):
        msg = 'SEARCH test had these errors in response sent by registry:'
        # Not tested at this time
        if (correct_id, correct_ip, correct_port) == (0, '0.0.0.0', 0) \
                and (resp_id, resp_ip, resp_port) != (0, '0.0.0.0', 0):

            msg += f'\n File should not be indexed, but {resp_id} {resp_ip}:{resp_port} sent in response.'
        elif (correct_id, correct_ip, correct_port) != (0, '0.0.0.0', 0) \
                and (resp_id, resp_ip, resp_port) == (0, '0.0.0.0', 0):

            msg += f'\n File indexed ({correct_id} {correct_ip}:{correct_port}), but registry responds it is not.'
        else:
            if resp_id != correct_id:
                msg += f'\n Peer ID {resp_id} in response instead of {correct_id}'
            if resp_ip != correct_ip:
                msg += f'\n IP {resp_ip} in response instead of {correct_ip}.'
            if resp_port != correct_port:
                msg += f'\n Port {resp_port} in response instead of {correct_port}.'
        raise TestError(msg)

def student_tx_search(node, fname):
    try:
        peer_id, ip, port = tx_search(node, fname)

        if None in (peer_id, ip, port):
            raise TestError('Recognizable SEARCH response not printed.')
    except AbnormalTerminationError:
        perror('Program unexpectedly closed during SEARCH test.')
        raise
    except DuplicateCommandError:
        perror('Multiple SEARCH responses printed.')
        raise
    except UnicodeDecodeError as err:
        perror(f'Program printed non-ASCII characters. {err}')
        raise EndTestsException() from err

    return peer_id, ip, port

def soln_tx_search(node, fname):
    try:
        peer_id, ip, port = tx_search(node, fname)

        if None in (peer_id, ip, port):
            raise TestError('Reconizable SEARCH response not sent by program.')
    except AbnormalTerminationError as ate:
        raise InternalError('Solution unexpectedly closed during SEARCH test.') from ate
    except DuplicateCommandError as dce:
        raise InternalError('Multiple SEARCH responses sent by program.') from dce
    except TestError as te:
        raise InternalError from te
    except UnicodeDecodeError as err:
        raise InternalError(f'Solution printed non-ASCII characters. {err}') from err

    return peer_id, ip, port

def tx_search(node, fname):
    node.sendline('SEARCH')
    enter_filename(node, fname)

    done = False
    peer_id = None
    ip = None
    port = None
    while not done:
        val = node.expect(
            [
                # PREFIX not printed to "user"
                r'[^\d]*(\d+)[^\d]+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*:\s*(\d+)[^\r]*\r\n',
                r'.*[Nn]ot\s*[Ii]ndex[^\r]*\r\n',
                r'.*[Nn]ot\s*[Ff]ound[^\r]*\r\n',
                pexpect.EOF,
                pexpect.TIMEOUT
            ], timeout=2)
        if val == 0:  # Id and address printed
            if peer_id is not None:
                raise DuplicateCommandError()
            peer_id = int(node.match.group(1))
            ip = node.match.group(2)
            port = int(node.match.group(3))

            # Check if program printed all 0s
            if peer_id == 0 and ip == '0.0.0.0' and port == 0:
                raise TestError('Search response for unindexed file printed as an indexed file. State the file was not found or not indexed.')

        elif val in (1, 2):  # Not indexed
            if peer_id is not None:
                raise DuplicateCommandError()
            peer_id = 0
            ip = '0.0.0.0'
            port = 0
        elif val == 3:  # EOF
            raise AbnormalTerminationError()
        elif val == 4:  # TIMEOUT
            done = True
        else:  # Error
            raise InternalError(f'tx_search had expect value {val}.')

    verify_alive(node)

    return peer_id, ip, port

def student_rx_search(node):
    try:
        fname, rx_id, ip, port = rx_search(node)

        if None in (fname, rx_id, ip, port):
            raise TestError('Reconizable SEARCH command not printed.')

    except DuplicateCommandError:
        perror('Multiple SEARCH responses printed.')
        raise
    except AbnormalTerminationError:
        perror('Program unexpectedly closed during SEARCH test.')
        raise
    except InvalidCommandError as err:
        perror(f'Incorrect response printed: "{err.message}"')
        raise
    except UnicodeDecodeError as err:
        perror(f'Program printed non-ASCII characters. {err}')
        raise EndTestsException() from err

    return fname, rx_id, ip, port

def soln_rx_search(node):
    try:
        fname, rx_id, ip, port = rx_search(node)

        if None in (fname, rx_id, ip, port):
            raise TestError('Reconizable SEARCH command not sent.')

    except DuplicateCommandError:
        perror('Multiple SEARCH commands sent.')
        raise
    except AbnormalTerminationError as ate:
        raise InternalError('Solution unexpectedly closed during SEARCH test.') from ate
    except InvalidCommandError as err:
        perror(f'Incorrect command sent: "{err.message}"')
        raise
    except UnicodeDecodeError as err:
        perror(f'Filename with non-ASCII characters sent in SEARCH command. {err}')
        raise EndTestsException() from err

    return fname, rx_id, ip, port

def rx_search(node):
    done = False
    fname = None
    rx_id = None
    ip = None
    port = None
    while not done:
        val = node.expect(
            [
                PREFIX + r'\s+SEARCH\s+(\S+)\s+(\d+)\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)[^\r]*\r\n',
                pexpect.EOF,
                pexpect.TIMEOUT,
                PREFIX + r'\s+(\S*)[^\r]*\r\n',
                ERRFIX + r'\s+([^\r]*)\r\n'
            ])
        if val == 0:  # SEARCH with arguments
            if rx_id is not None:
                raise DuplicateCommandError()
            fname = node.match.group(1)
            rx_id = int(node.match.group(2))
            ip = node.match.group(3)
            port = int(node.match.group(4))
        elif val == 1:  # EOF
            raise AbnormalTerminationError()
        elif val == 2:  # TIMEOUT
            done = True
        elif val == 3:  # Incorrect command
            raise InvalidCommandError(" ".join(node.after.split()[1:]))
        elif val == 4:  # Error
            raise TestError(node.match.group(1))
        else:  # Error
            raise InternalError(f'rx_search had expect value {val}.')

    verify_alive(node)

    return fname, rx_id, ip, port

def enter_filename(node, fname):
    val = node.expect(
        [
            r'(?i)[^\r]*[Ff]ile\s*name[^:]*:',
            pexpect.EOF,
            pexpect.TIMEOUT
        ], timeout=1)
    if val == 1:
        raise AbnormalTerminationError()
    if val == 2:  # Timeout, do nothing if prompt appeared
        msg = 'Missing or unrecognized filename prompt.\nEnsure you use [Ff]ilename and \':\''
        raise TestError(msg)
    node.sendline(fname)

################### FETCH functions ###################################
def student_perform_fetch(reg, peer, remotes, src_path, dst_path):
    fname = os.path.basename(src_path)
    if fname != os.path.basename(dst_path):
        raise InternalError(f'Different filenames provided to student_perform_fetch, source:{fname} destination:{os.path.basename(dst_path)}.')

    banner(f'Performing FETCH test for file "{fname}"')

    student_tx_fetch(peer, fname)

    # check SEARCH at registry
    rx_fname, correct_id, correct_ip, correct_port = soln_rx_search(reg)
    if rx_fname != fname:
        raise TestError(f'Program SEARCHed for file {rx_fname} instead of {fname}.')

    # check FETCH at remote peer specified by registry output
    remote = None
    for tmp in remotes:
        if tmp[1] == correct_id:
            remote = tmp[0]
            src_path = os.path.join(tmp[4], src_path)
    if remote is None:
        raise InternalError(f'Unable to find peer with ID {correct_id} based on SEARCH output.')

    fetch_fname = soln_rx_fetch(remote, fname)
    if fetch_fname != fname:
        raise TestError(f'Program sent FETCH command for file {fetch_fname} instead of {fname}.')

    wait_for_download(peer)

    compare_files(src_path, dst_path)

def student_tx_fetch(node, fname):
    try:
        tx_fetch(node, fname)
    except AbnormalTerminationError:
        perror(f'Program unexpectedly closed during FETCH test.')
        raise
    except UnicodeDecodeError as err:
        perror(f'Program printed non-ASCII characters. {err}')
        raise EndTestsException() from err

def soln_tx_fetch(node):
    raise InternalError('soln_tx_fetch not implemented')

def tx_fetch(node, fname):

    node.sendline('FETCH')
    enter_filename(node, fname)

    verify_alive(node)

def student_rx_fetch(node):
    raise InternalError('student_rx_fetch not implemented')

def soln_rx_fetch(node, fname):
    try:
        fetch_fname = rx_fetch(node)

        if fetch_fname is None:
            raise TestError('Recongnizable FETCH command not sent.')
        if fetch_fname != fname:
            raise TestError(f'FETCH request for {fetch_fname} instead of {fname}.')

    except AbnormalTerminationError:
        raise InternalError('Solution unexpectedly closed during FETCH test.')
    except DuplicateCommandError:
        perror('Multiple FETCH commands sent.')
        raise
    except InvalidCommandError as err:
        perror(f'Incorrect command sent: "{err.message}"')
        raise
    except UnicodeDecodeError as err:
        perror(f'Filename with non-ASCII characters sent in FETCH command. {err}')
        raise EndTestsException()

    return fname

def rx_fetch(node):
    done = False
    fname = None
    while not done:
        val = node.expect([
            PREFIX+r'\s+FETCH\s+([^\r]+)\r\n',
            pexpect.EOF,
            pexpect.TIMEOUT,
            PREFIX+r'\s+(\S*)[^\r]*\r\n',
            ERRFIX+r'\s+([^\r]*)\r\n'
            ], timeout=2)
        if val == 0: # FETCH with argument
            if fname is not None:
                raise DuplicateCommandError()
            fname = node.match.group(1)
        elif val == 1: # EOF
            raise AbnormalTerminationError()
        elif val == 2: # TIMEOUT
            done = True
        elif val == 3: # Incorrect command
            raise InvalidCommandError(" ".join(node.after.split()[1:]))
        elif val == 4: # Error
            raise TestError(node.match.group(1))
        else: # Error
            raise InternalError(f'rx_fetch had expect value {val}.')

    verify_alive(node)

    return fname

def compare_files(server_path, client_path):
    # Exists
    if (not os.path.isfile(server_path)) or (not os.access(server_path, os.R_OK)):
        raise TestError('File does not exist or is not readable at server.')
    if (not os.path.isfile(client_path)) or (not os.access(client_path, os.R_OK)):
        raise TestError('File does not exist or is not readable at client.')
    # Check file access and equivalence
    if not filecmp.cmp(server_path, client_path, shallow=False):
        client_stat = os.lstat(client_path)
        server_stat = os.lstat(server_path)
        if client_stat.st_size != server_stat.st_size:
            raise TestError(f'File at server has size {server_stat.st_size}, while client file has size {client_stat.st_size}')
        else:
            raise TestError('Files at server and client have the same size, but different contents.')

def wait_for_download(node):
    try:
        # Wait for transfer to complete
        val = node.expect([pexpect.TIMEOUT, r'[^:]*:'],
                timeout=DOWNLOAD_TIMEOUT) # Transfer may take a long time
        if val == 0: # TIMEOUT
            raise TestError('Download took too long or program produced an unrecognizable prompt.')
        elif val == 1: # Prompt, do nothing
            pass
        else: # ERROR
            raise InternalError(f'wait_for_prompt had expect value {val}.')

    except UnicodeDecodeError as err:
        perror(f'Program printed non-ASCII characters. {err}')
        raise EndTestsException() from err

    verify_alive(node)

################### REGISTER functions ###################################

def soln_perform_register(reg, peer, soln_id):
    tx_ip, tx_port = soln_tx_register(peer)
    if tx_ip is None:
        raise InternalError('Solution peer did not print a recognizable ADDR response.')
    peer_id, ip, port = soln_rx_register(reg)
    if soln_id != peer_id:
        raise InternalError(f'Solution peer REGISTERed id {peer_id} instead of {soln_id}.')
    if (tx_ip, tx_port) != (ip, port):
        raise InternalError(f'Solution peer REGISTERed address {ip}:{port} instead of {tx_ip}:{tx_port}.')

    return peer_id, ip, port

def soln_tx_register(node):
    try:
        return tx_register(node)
    except AbnormalTerminationError as ate:
        raise InternalError('Solution peer unexpectedly closed during REGISTER.') from ate
    except DuplicateCommandError as err:
        raise InternalError('Solution peer printed duplicate ADDR results during REGISTER.') from err
    except InvalidCommandError as err:
        raise InternalError(f'Solution peer printed unexpected result during REGISTER "{err.message}".') from err
    except TestError as err:
        raise InternalError(f'Solution peer generated error during REGISTER "{err.message}".')

def tx_register(node):
    node.sendline('REGISTER')

    done = False
    ip = None
    port = None
    while not done:
        val = node.expect([
            PREFIX+r'\s+ADDR\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*:\s*(\d+)[^\r]*\r\n',
            pexpect.EOF,
            pexpect.TIMEOUT,
            PREFIX+r'\s+(\S*)[^\r]*\r\n',
            ERRFIX+r'\s+([^\r]*)\r\n'
            ], timeout=2)
        if val == 0: # Address printed
            if ip is not None:
                raise DuplicateCommandError()
            ip = node.match.group(1)
            port = int(node.match.group(2))
        elif val == 1: # EOF
            raise AbnormalTerminationError()
        elif val == 2: # TIMEOUT
            done = True
        elif val == 3: # Incorrect command
            raise InvalidCommandError(" ".join(node.after.split()[1:]))
        elif val == 4: # Error
            raise TestError(node.match.group(1))
        else: # Error
            raise InternalError(f'tx_register had expect value {val}.')

    verify_alive(node)

    return ip, port

def soln_rx_register(node):
    try:
        peer_id, ip, port = rx_register(node)
        if None in (peer_id, ip, port):
            raise TestError('Peer did not send recognizable REGISTER request.')
    except DuplicateCommandError as err:
        raise InternalError('Solution peer sent duplicate REGISTER requests.') from err
    except AbnormalTerminationError as ate:
        raise InternalError('Solution registry unexpectedly closed during REGISTER.') from ate
    except InvalidCommandError as err:
        raise InternalError(f'Solution registry sent invalid command "{err.message}" during REGISTER.')
    # Students do not handle REGISTER commands, so all errors become InternalErrors
    except TestError as err:
        raise InternalError(f'Error during REGISTER operation "{err.message}".') from err

    return peer_id, ip, port

def rx_register(node):
    done = False
    peer_id = None
    ip = None
    port = None
    while not done:
        val = node.expect([
            PREFIX+r'\s+REGISTER\s+(\d+)\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*:\s*(\d+)[^\r]*\r\n',
            pexpect.EOF,
            pexpect.TIMEOUT,
            PREFIX+r'\s+(\S*)[^\r]*\r\n',
            ERRFIX+r'\s+([^\r]*)\r\n'
            ], timeout=2)
        if val == 0: # Id and address printed
            if peer_id is not None:
                raise DuplicateCommandError()
            peer_id = int(node.match.group(1))
            ip = node.match.group(2)
            port = int(node.match.group(3))
        elif val == 1: # EOF
            raise AbnormalTerminationError()
        elif val == 2: # TIMEOUT
            done = True
        elif val == 3: # Incorrect command
            raise InvalidCommandError(" ".join(node.after.split()[1:]))
        elif val == 4: # Error
            raise TestError(node.match.group(1))
        else: # Error
            raise InternalError(f'rx_register had expect value {val}.')

    verify_alive(node)

    return peer_id, ip, port

################### EXIT functions ###################################

def student_perform_exit(reg, peer):
    banner('Performing EXIT test')
    student_tx_exit(peer)
    soln_rx_exit(reg)

def soln_perform_exit(reg, peer):
    soln_tx_exit(peer)
    try:
        soln_rx_exit(reg)
    except TestingErrorBase as err:
        raise InternalError(err.message)

def student_tx_exit(node):
    try:
        tx_exit(node)
    except TestError as err:
        raise TestError('Program failed to close in EXIT test.') from err
    except AbnormalTerminationError as err:
        raise TestError(err.message) from err

def soln_tx_exit(node):
    try:
        tx_exit(node)
    except TestError as err:
        raise InternalError('Solution failed to close in EXIT test.') from err

def tx_exit(node):
    node.sendline('EXIT')
    verify_dead(node)

def student_rx_exit(node):
    raise InternalError('student_rx_exit not tested')
    try:
        rx_exit(node)
    except InvalidCommandError as err:
        perror(f'Command printed incorrectly for EXIT command: "{err.message}"')
        raise
    except AbnormalTerminationError as ate:
        raise TestError('Program unexpectedly closed.') from ate

def soln_rx_exit(node):
    try:
        rx_exit(node)
    except InvalidCommandError as err:
        perror(f'Incorrect command sent: "{err.message}".')
        raise
    except AbnormalTerminationError as ate:
        raise InternalError('Solution closed during EXIT test.') from ate

def rx_exit(node):
    done = False
    while not done:
        val = node.expect(
            [
                PREFIX + r'\s+(\S*)[^\r]*\r\n',
                pexpect.EOF,
                pexpect.TIMEOUT,
                ERRFIX + r'\s+([^\r]*)\r\n'
            ])
        if val == 0:  # Incorrect command
            raise InvalidCommandError(" ".join(node.after.split()[1:]))
        if val == 1:  # EOF
            raise AbnormalTerminationError()
        if val == 2:  # TIMEOUT
            done = True
        elif val == 3:  # Error
            raise TestError(node.match.group(1))
        else:  # Error
            raise InternalError(f'rx_exit had expect {val}.')

    verify_alive(node)

################### Generic functions ###################################

def verify_alive(node):
    val = node.expect(
        [
            pexpect.EOF,
            pexpect.TIMEOUT
        ], timeout=0.2)
    if val == 0 or not node.isalive():
        raise AbnormalTerminationError()

def verify_dead(node):
    val = node.expect(
        [
            pexpect.EOF,
            pexpect.TIMEOUT
        ], timeout=0.2)
    if val == 1 and node.isalive():
        raise TestError()
    node.close()
    if node.exitstatus != 0 or node.exitstatus is None:
        raise AbnormalTerminationError('Non-zero exit status used under normal EXIT.')

def initial_setup(base_files, base_exes, required_exes):
    global tmp_dir

    # Temporary directory name
    # Default name used with keep argument, changed if using tempfile class
    tmp_dirname = os.path.join(os.getcwd(), 'tmp_local_dir_for_check')

    do_debug, do_keep = parse_args()

    script_dir = os.path.dirname(__file__)

    # Use absolute paths
    base_files = [os.path.abspath(os.path.join(script_dir, f)) for f in base_files]
    base_exes = [os.path.abspath(os.path.join(script_dir, f)) for f in base_exes]
    # All remaining arguments are user files
    user_files = list(map(os.path.abspath, sys.argv[1:]))

    # Check for temporary testing directory
    if do_keep and os.path.isdir(tmp_dirname):
        print(f'Temporary directory "{os.path.basename(tmp_dirname)}" exists, remove it before running checks.')
        sys.exit()

    # Verify all base_files are present and readable using recursion as needed
    missing = []
    for f in base_files:
        if os.path.isfile(f):
            if not os.access(f, os.R_OK):
                missing.append(f)
        elif os.path.isdir(f):
            if not os.access(f, os.R_OK | os.X_OK):
                missing.append(f)
            else:
                for root, dirs, files in os.walk(f, followlinks=True):
                    for d in dirs:
                        if not os.access(os.path.join(root, d), os.R_OK | os.X_OK):
                            missing.append(d)
                    for n in files:
                        if not os.access(os.path.join(root, n), os.R_OK):
                            missing.append(n)
        else:
            missing.append(f)
    if len(missing) > 0:
        print('Required base files are missing or not readable.')
        print(f'Problem files or dirs: {" ".join(map(os.path.basename,missing))}')
        sys.exit()

    # Verify all base_exes are present and usable
    missing = []
    for f in base_exes:
        if (not os.path.isfile(f)) or (not os.access(f, os.R_OK | os.X_OK)):
            missing.append(f)
    if len(missing) > 0:
        print('Required base executables are missing or have the wrong permissions.')
        print(f'Missing executables: {" ".join(map(os.path.basename,missing))}')
        sys.exit()

    # Verify all argument files are not in provided files or a target executable
    banner('Evaluating the following files:')
    all_bases = list(map(os.path.basename, base_files + base_exes + required_exes))
    for f in map(os.path.basename, user_files):
        # Search for supplied files in base_files and base_exe
        found = None
        print(f'{os.path.basename(f)}', end='')
        if f in all_bases:
            found = f

        # Search for supplied files in any base_files directories
        for d in filter(os.path.isdir, base_files):
            for root, dirs, files in os.walk(d):
                if f in files:
                    found = f

        if found is not None:
            print(f'*\n\nFile {found} is provided with the assignment or an executable, do not submit it.')
            sys.exit()
        print('')

    # Ensure the supplied files are readable and not a directory
    for f in user_files:
        if (not os.path.isfile(f)) or (not os.access(f, os.R_OK)):
            print(f'\n"{os.path.basename(f)}" does not exist, is not readable, or is a directory.')
            print('Check permissions and do not submit directories.')
            sys.exit()

    # Verify all user files meet requirements
    validate_sources(user_files)

    # Create the temporary testing directory
    tmp_dir = None
    if do_keep:
        try:
            os.mkdir(tmp_dirname, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        except FileExistsError as err:
            print(f'Error creating temporary directory "{os.path.basename(tmp_dirname)}": {err.strerror}')
            sys.exit()
    else:
        tmp_dir = tempfile.TemporaryDirectory()
        tmp_dirname = tmp_dir.name

    # Copy the argument files, base_files, and base_exes into the tempdir
    for f in user_files:
        shutil.copy(f, tmp_dirname)
    for f in base_files + base_exes:
        if os.path.isdir(f):
            shutil.copytree(f, os.path.join(tmp_dirname, os.path.basename(f)))
        else:
            shutil.copy(f, tmp_dirname)

    os.chdir(tmp_dirname)

    # Compile the executables
    banner("Attempting to build the executables.")
    logfile = None
    if do_debug:
        logfile = sys.stdout
    compiler = pexpect.spawn('make', encoding='utf-8', logfile=logfile)
    done = False
    while not done:
        val = compiler.expect([
            r'.*(gcc|cc|g\+\+)[^:].*\r\n',
            r'.*:.*\r\n',
            pexpect.EOF
        ])
        if val == 0:  # Compile command
            if compiler.after.find('-w') != -1:
                print(compiler.after, end='')
                print(compiler.read())
                print('\nThe -w compiler flag disables warnings and is not allowed. Remove it and try again.')
                sys.exit()
            if compiler.after.find('-Wall') == -1:
                # Not required for link commands, only examine commands using source files
                if any(compiler.after.find(ext) != -1 for ext in ['.c', '.cc', '.cpp', '.cxx', '.C']):
                    print(compiler.after, end='')
                    print(compiler.read(), end='')
                    print('\n-Wall flag missing from compile command, add it.')
                    sys.exit()
        elif val == 1:  # Compile or make error
            print(compiler.after, end='')
            print(compiler.read())
            print('Compile error or warning, correct your code.')
            sys.exit()
        elif val == 2:  # EOF
            done = True
            compiler.close()
            if compiler.exitstatus != 0:
                raise InternalError('make returned non-zero value.')
        else:
            raise InternalError('Unexpcted return from expect() during make.')

    required_exes = [os.path.abspath(os.path.join(tmp_dirname, f)) for f in required_exes]
    for f in required_exes:
        if (not os.path.isfile(f)) or (not os.access(f, os.X_OK)):
            print(f'\nExecutable "{os.path.basename(f)}" required, but not created by make or not executable.')
            sys.exit()

    banner('Compilation successful')

    return do_debug

def start_registry(exe, port, timeout, soln=True, do_debug=False):
    args = [str(port)]
    if soln:
        args.append('-t')
        if do_debug:
            args.append('-d')

    logfile=None
    if do_debug:
        logfile=sys.stdout
        print(f'[INFO] Command line: {exe} {" ".join(args)}')
    reg = pexpect.spawn(os.path.join('.', exe),
                        args,
                        timeout=timeout,
                        encoding='utf-8',
                        logfile=logfile)

    # Let the server complete startup before starting client
    try:
        verify_alive(reg)
    except AbnormalTerminationError as ate:
        msg = 'Registry unexpectedly quit.'
        if soln:
            raise InternalError(msg) from ate
        raise AbnormalTerminationError(msg) from ate
    else:
        # Kill the registry if the program terminates
        atexit.register(reg.terminate, True)

    return reg

def random_files(count):
    files = []
    for _ in range(count):
        name = "".join(random.choices(string.ascii_letters + string.digits, k=random.randint(3, 12)))
        files.append(name)

    return files

def start_peer(exe, host, port, peer_id, wd, files, shared_dir, soln=False, do_debug=False, copy=False):
    args = [host, str(port), str(peer_id)]
    if soln:
        args.append('-t')
        if do_debug:
            args.append('-d')

    # Setup the peer files to PUBLISH
    dst = os.path.join(wd, shared_dir)
    os.makedirs(dst)
    if soln:
        shutil.copy(exe, os.path.join(wd, exe))
    else:
        os.rename(exe, os.path.join(wd, exe))
    for fname in files:
        if copy:
            shutil.copy(os.path.join(os.getcwd(), fname), dst)
        else:
            open(os.path.join(wd, shared_dir, fname), 'w').close()

    # Start the peer
    logfile=None
    if do_debug:
        logfile=sys.stdout
        print(f'[INFO] Command line: {exe} {" ".join(args)}')
    peer = pexpect.spawn(os.path.join(os.getcwd(), wd, exe),
                         args,
                         cwd=os.path.join(os.getcwd(), wd),
                         encoding='utf-8',
                         logfile=logfile)

    try:
        verify_alive(peer)
    except AbnormalTerminationError as ate:
        print(peer.read())
        msg = 'Peer unexpectedly closed.'
        if soln:
            raise InternalError(msg) from ate
        else:
            perror(msg)
        raise AbnormalTerminationError(msg) from ate
    else:
        # Kill the peer if the program terminates
        atexit.register(peer.terminate, True)

    return peer

def parse_args():
    HELP_ARG = '-h'
    DEBUG_ARG = '-d'
    KEEP_ARG = '-k'

    do_help = False
    do_debug = False
    do_keep = False

    # Parse the user arguments
    for arg in sys.argv[1:]:
        if arg == HELP_ARG:
            do_help = True
            sys.argv.remove(arg)
        elif arg == DEBUG_ARG:
            do_debug = True
            sys.argv.remove(arg)
        elif arg == KEEP_ARG:
            do_keep = True
            sys.argv.remove(arg)
        # Assume all other arguments are files

    # Print help message if needed
    if (len(sys.argv) == 1) or do_help:
        if len(sys.argv) == 1:
            print('ERROR: No files provided to script.\n')

        print(f'Usage: [options] {sys.argv[0]} <file1> <file2> ....')
        print('  Include all files for your assignment as arguments to the script.')
        print('  Options:')
        print(f'    {HELP_ARG} : Print this help and usage message.')
        print(f'    {DEBUG_ARG} : Print program output and debug messages. Default is off.')
        print(f'    {KEEP_ARG} : Do not delete temporary directory when script terminates.', end='')
        print(' Default is off (delete directory).')
        sys.exit()

    return do_debug, do_keep

def validate_sources(files):

    # Check for invalid strings
    for f_name in files:
        with open(f_name) as f:
            data = f.read()
            if 'sleep' in data:
                print('** Warning: sleep-type functions are not permitted.')
            if 'MSG_WAITALL' in data:
                print('** Warning: socket flags, such as MSG_WAITALL, are not permitted.')
            if 'ioctl' in data:
                print('** Warning: ioctl function calls are not permitted.')
            if 'setsockopt' in data:
                print('** Warning: setsockopt function calls are not permitted.')
            if 'FD_SETSIZE' in data:
                print('** Warning: FD_SETSIZE constant is not permitted as an argument to select. It is not what you want/need.')

def get_random_port():
    return random.randint(2 ** 15, 2 ** 16 - 1)

def get_random_id():
    return random.randint(2 ** 31, 2 ** 32 - 1)

def banner(msg):
    print('\n' + '%' * len(msg))
    print(msg)
    print('%' * len(msg))

def subbanner(msg):
    print('  ' + '-' * len(msg))
    print(f'  {msg}')
    print('  ' + '-' * len(msg))

def perror(msg):
    print('ERROR: ' + msg)

################### Globals ############################
# Prefix required before all program output interpreted by script
PREFIX = 'TEST]'

# Error prefix printed by solutioni programs
ERRFIX = 'ERROR]'

DOWNLOAD_TIMEOUT = 300

# Ensure any temporary directory remains in scope for the entire execution
# Created in initial_setup
tmp_dir = None
