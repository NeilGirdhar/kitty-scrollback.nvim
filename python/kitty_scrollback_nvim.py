#!/usr/bin/env python3
from typing import List
from kitty.boss import Boss
from kittens.tui.handler import result_handler
from kitty.fast_data_types import get_options

import json
import os
import inspect

ksb_dir = os.path.dirname(
    os.path.dirname(os.path.abspath(inspect.getfile(lambda: None))))


def main():
    raise SystemExit('Must be run as kitten kitty_scrollback_nvim')


# based on kitty source window.py
def pipe_data(w, target_window_id, ksb_dir, config_file):
    kitty_opts = get_options()
    data = {
        'scrolled_by': w.screen.scrolled_by,
        'cursor_x': w.screen.cursor.x + 1,
        'cursor_y': w.screen.cursor.y + 1,
        'lines': w.screen.lines,
        'columns': w.screen.columns,
        'window_id': int(target_window_id),
        'ksb_dir': ksb_dir,
        'kitty_opts': {
            "shell_integration":
            w.child.environ.get('KITTY_SHELL_INTEGRATION', 'disabled').split(),  # env takes precedence over config
            "scrollback_fill_enlarged_window":
            kitty_opts.scrollback_fill_enlarged_window,
            "scrollback_lines":
            kitty_opts.scrollback_lines,
            "scrollback_pager":
            kitty_opts.scrollback_pager,
            "allow_remote_control":
            kitty_opts.allow_remote_control,
            "listen_on":
            kitty_opts.listen_on,
            "scrollback_pager_history_size":
            kitty_opts.scrollback_pager_history_size
        }
    }
    if config_file:
        data['config_file'] = config_file
    return data


def parse_nvim_args(args):
    for idx, arg in enumerate(args):
        if arg.startswith('--no-nvim-args'):
            return ()
        if arg.startswith('--nvim-args'):
            if idx + 1 < len(args):
                return tuple(filter(None, args[idx + 1:]))
            return ()
    return (
        '--clean',
        '--noplugin',
        '-n',
    )


def parse_nvim_appname(args):
    for idx, arg in enumerate(args):
        if arg.startswith('--nvim-appname') and (idx + 1 < len(args)):
            return ('--env', f'NVIM_APPNAME={args[idx + 1]}')
    return ()


def parse_config_file(args):
    for idx, arg in enumerate(args):
        if arg.startswith('--config-file') and (idx + 1 < len(args)):
            config_args = args[idx + 1]
            return config_args
    return None


@result_handler(type_of_input=None, no_ui=True, has_ready_notification=False)
def handle_result(args: List[str],
                  result: str,
                  target_window_id: int,
                  boss: Boss) -> None:
    w = boss.window_id_map.get(target_window_id)
    if w is not None:
        config_file = parse_config_file(args[1:])
        kitty_data = json.dumps(
            pipe_data(w,
                      target_window_id,
                      ksb_dir,
                      config_file))

        kitty_args = (
            '--copy-env',
            '--type',
            'overlay',
            '--title',
            'kitty-scrollback.nvim',
        ) + parse_nvim_appname(args[1:])

        nvim_args = parse_nvim_args(args[1:]) + (
            '--cmd',
            ' lua vim.api.nvim_create_autocmd([[VimEnter]], { '
            '   group = vim.api.nvim_create_augroup([[KittyScrollBackNvimVimEnter]], { clear = true }), '
            '   pattern = [[*]], '
            '   callback = function() '
            f'   vim.opt.runtimepath:append([[{ksb_dir}]])'
            f'   require([[kitty-scrollback.launch]]).setup_and_launch([[{kitty_data}]])'
            '  end, '
            ' })')

        cmd = ('launch', ) + kitty_args + ('nvim', ) + nvim_args
        boss.call_remote_control(w, cmd)
    else:
        raise Exception(f'Failed to get window with id: {target_window_id}')
