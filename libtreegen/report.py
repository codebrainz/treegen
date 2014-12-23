import os
import sys

__all__ = [ "set_error_stream", "error", "warning", "note" ]

error_stream  = sys.stderr
terminal_out  = error_stream.isatty() if hasattr(error_stream, "isatty") else False
show_context  = True

BLACK   = '\x1B[30m'
RED     = '\x1B[31m'
GREEN   = '\x1B[32m'
YELLOW  = '\x1B[33m'
BLUE    = '\x1B[34m'
MAGENTA = '\x1B[35m'
CYAN    = '\x1B[36m'
WHITE   = '\x1B[37m'
BOLD    = '\x1B[1m'
RESET   = '\x1B[0m'

PREFIX_COLOR = {
    "error":   RED,
    "warning": MAGENTA,
    "note":    CYAN,
}

# TODO: change to set_streams(err_stream, out_stream, use_colors) and use
#       different stream for non-error output.
def set_error_stream(stream=sys.stderr, use_colors=True, show_context_text=True):
    global error_stream, terminal_out, show_context
    old_error_stream = error_stream
    if stream is not None:
        error_stream = stream
    else:
        error_stream = open(os.devnull, 'w')
    terminal_out = False
    if use_colors and hasattr(error_stream, "isatty"):
        terminal_out = error_stream.isatty()
    show_context = show_context_text
    return old_error_stream

def _get_context(filename, line, column):
    line_text = ''
    with open(filename, 'r') as file:
        for num, text in enumerate(file, 1):
            if num == line:
                line_text = text.rstrip()
                break
    if line_text:
        line_text = '\t' + line_text + '\n\t'
        for i in range(column-2): # WTF!? why 2? should be 1 at most
            line_text += ' '
        line_text += GREEN + BOLD + '^' + RESET + '\n'
    return line_text

# TODO: could grep message for single quote pairs and make bold to highlight them
def _log_msg(stream, prefix, message, loc, fatal, show_context_line=True):
    if terminal_out:
        stream.write(PREFIX_COLOR.get(prefix, BLUE) + BOLD + prefix + ':' + RESET + ' ')
    else:
        stream.write(prefix + ': ')
    if loc:
        location_str = '%s:%d:%d' % (loc.file, loc.line, loc.column)
        if terminal_out:
            stream.write(BOLD + location_str + RESET + ': ')
        else:
            stream.write(location_str + ': ' % location)
    stream.write(message + '\n')
    if loc and show_context and show_context_line:
        context = _get_context(*loc)
        if context:
            stream.write(context)
    if fatal:
        sys.exit(1)
    else:
        stream.flush()

def error(message, location=None, fatal=True, show_context_line=True):
    _log_msg(error_stream, "error", message, location, fatal, show_context_line)

def warning(message, location=None, fatal=False, show_context_line=True):
    _log_msg(error_stream, "warning", message, location, fatal, show_context_line)

def note( message, location=None, fatal=False, show_context_line=True):
    _log_msg(error_stream, "note", message, location, fatal, show_context_line)
