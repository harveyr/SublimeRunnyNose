import os
import re
import sublime
import sublime_plugin
import subprocess
import datetime


class RunnyNoseShowPanelCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        sublime.active_window.run_command(
            'show_panel', {'panel': 'output.nosetest_panel'})


class RunnyNoseCommand(sublime_plugin.TextCommand):
    @property
    def current_scope(self):
        return self.view.scope_name(self.view.sel()[0].begin())

    def run(self, edit):
        test_file = self.view.file_name()
        if not test_file.endswith('.py'):
            print('RunnyNose: Ignoring non-Python file ' + test_file)
            return

        head, tail = os.path.split(test_file)
        self.path = head
        self.file_name = tail

        self.view_contents = self.view.substr(
            sublime.Region(0, self.view.size())
        )

        method = self.get_test_method()
        if not method:
            print("RunnyNose: No test method found.")
            return

        venv_cmd = self.get_virtualenv_source_cmd()
        if not venv_cmd:
            print("Couldn't find bin/activate")
            return

        cmd = "{venv};nosetests {file}:{cls}.{method}".format(
            venv=self.get_virtualenv_source_cmd(),
            cls=self.get_class(),
            file=self.file_name,
            method=method)

        window = sublime.active_window()
        panel = window.create_output_panel('nosetest_panel')
        panel_text = ('Running {method} at {time}\n{cmd}'.format(
            method=method,
            time=datetime.datetime.now(),
            cmd=cmd))
        panel.insert(edit, 0, panel_text)
        window.run_command('show_panel', {'panel': 'output.nosetest_panel'})
        p = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        result = err.decode('utf-8') + out.decode('utf-8')
        panel.insert(
            edit,
            panel.size(),
            result
        )

    def get_class(self):
        class_search = re.search(r'class (\w+)\(', self.view_contents)
        if class_search:
            return class_search.groups(0)[0]
        else:
            return None

    def get_test_method(self):
        line = self.view.line(self.view.sel()[0])
        contents = self.view.substr(sublime.Region(0, line.end()))
        hits = [h for h in
                re.findall(r'\s*def (test\w*)\(', contents)]
        if len(hits) > 0:
            return hits[-1]
        return False

    def get_virtualenv_source_cmd(self):
        """
        Finds bin/activate and returns the command to source it.

        This feels hacky, and I think there's a way to activate the virtualenv
        programmatically. However, I'm concerned about the side effects of
        doing that within a Sublime plugin.
        """

        path_parts = self.path.split('/')
        search_paths = ['.']
        for i in range(len(path_parts)):
            search_paths.append('/'.join(path_parts[:-i]))
        for path in search_paths:
            if not path:
                continue
            subpaths = [o for o in os.listdir(path) if
                        os.path.isdir(os.path.join(path, o))]
            if 'bin' in subpaths:
                bin_path = os.path.join(path, 'bin')
                if 'activate' in os.listdir(bin_path):
                    return 'source {}/bin/activate'.format(path)
        return ''

    def is_enabled(self):
        return 'source.python' in self.current_scope

    def is_visible(self):
        return 'source.python' in self.current_scope

    def strip_colors(self, text):
        return re.sub(r'\033\[[0-9;]+m|\x1b|\[2K', '', text, re.UNICODE)
