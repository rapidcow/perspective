import io
import json
import shlex

def test_shlex():
    with io.StringIO('TOKEN HELP i have a "str\ning" moment\r\n'
                     'NEKOT but,, backward and has \\ \\\t\\n\\ escapes\n') as fp:
        lexer = shlex.shlex(fp, posix=True, punctuation_chars='\r\n')
        lexer.whitespace = ' \t'
        # please make this work
        lexer.lineno = 100
        # lexer.escape = '\\'
        while True:
            # don't use read_token()!!
            tok = lexer.get_token()
            if tok == lexer.eof:
                break
            print(f'{fp.tell():02}', lexer.lineno, repr(tok))

# keeping track of the line number is gonna be a challenge...
# whenever we need to parse JSON, it seems like we have no immediate
# solution but to read the rest of the stream...
def test_decoder():
    with io.StringIO(
        """STUFF {
            "something": true,
            "other": 123.4
        }
        OTHER stuff is \t here 2023-03-03
        """) as fp:
        lexer = shlex.shlex(fp, posix=True, punctuation_chars='\r\n')
        lexer.whitespace = ' \t'
        while True:
            tok = lexer.get_token()
            if tok == lexer.eof:
                break
            print(f'{fp.tell():02}', repr(tok))
            if tok == 'STUFF':
                decoder = json.JSONDecoder()
                curr = fp.tell()
                obj, idx = decoder.raw_decode(fp.getvalue(), curr)
                print(f'scanned {obj!r} until {idx}')
                fp.seek(idx)
                assert lexer.get_token() == '\n'
            else:
                while tok != '\n':
                    tok = lexer.get_token()
                    print('>', f'{fp.tell():02}', repr(tok))

def test_empty():
    with io.StringIO(
        """STUFF a

        what?!

                OTHER stuff is here

        # a comment that # should # be ignored ####
        ALTHOUGH   # this comment is only partially ignored

            l
        """) as fp:
        lexer = shlex.shlex(fp, posix=True)
        lexer.whitespace = ' '
        while True:
            tok = lexer.get_token()
            if tok == lexer.eof:
                break
            print(f'{fp.tell():02} {lexer.lineno} {tok!r}')

test_shlex()
print('-' * 24)
test_decoder()
print('-' * 24)
test_empty()
