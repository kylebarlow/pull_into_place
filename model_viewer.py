#!/usr/bin/env python2
# encoding: utf-8

""" 
Plot the position of the Glu38 carboxyl moiety (in terms of distance from the 
catalytic position) against the score of the model.  I'm looking for designs 
that have energy funnels focused on the desired Glu38 position.

Usage:
    score-vs-rmsd.py [options] <directories>...

Options:
    -f --force          Force the cache to be regenerated.
    -q --quiet          Build the cache, but don't launch the GUI.
    -i --interesting    Filter uninteresting designs by default.
    -x --xlim XLIM      Set the x-axis limit for all distance metrics.
"""

# Imports (fold)
import collections
import docopt
import glob
import gtk
import matplotlib
import matplotlib.pyplot
import os
import pango
import re
import shutil
import yaml

from numpy import *
from biophysics import pdb
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg
from matplotlib.backends.backend_gtkagg import NavigationToolbar2GTKAgg


class Model:

    def __init__(self, directory, use_cache=True):
        self.directory = directory
        self.cache_path = os.path.join(directory, 'cache.npz')
        self.notes_path = os.path.join(directory, 'notes.txt')
        self.interest_path = os.path.join(directory, 'interesting')
        self.rep_path = os.path.join(directory, 'representative.txt')
        self.sequence_path = os.path.join(directory, 'sequence.txt')

        self.paths = []
        self.scores = None
        self.loop_rmsds = None
        self.cooh_dists = None
        self.sequence = None
        self.loop_sequence = None
        self._notes = ""
        self._interesting = False
        self._representative = None

        self._load_annotations()
        #self._load_sequence()
        self._load_scores_and_dists(use_cache)

    def __str__(self):
        return '<' + self.fancy_path + '>'

    def __len__(self):
        return len(self.paths)


    def get_notes(self):
        return self._notes

    def set_notes(self, notes):
        self._notes = notes
        self._save_notes()

    def get_interest(self):
        return self._interest

    def set_interest(self, interest):
        self._interest = interest
        self._save_interest()

    def get_representative(self):
        if self._representative is None:
            return argmin(self.scores)
        else:
            return self._representative

    def set_representative(self, index):
        self._representative = index
        self._save_representative()

    def get_representative_path(self):
        return self.paths[self.representative]

    def get_distances(self, metric):
        if metric == "Loop RMSD":
            return self.loop_rmsds

        elif metric == "COOH RMSD":
            return self.cooh_dists

        elif metric == "Max COOH Distance":
            return self.cooh_dists

        else:
            raise ValueError, "Unknown distance metric '{}'.".format(metric)

    def get_fancy_path(self, extension=''):
        return 'glu_{}.delete_{}.round_{}.{}{}'.format(
                self.glu_position, self.num_deletions, self.round, self.name,
                extension)

    @property
    def glu_position(self):
        job, model = os.path.split(self.directory)
        match = re.search('glu_(\d+)', job)
        return int(match.group(1)) if match else 38

    @property
    def num_deletions(self):
        job, model = os.path.split(self.directory)
        match = re.search('delete_(\d+)', job)
        return int(match.group(1)) if match else 0

    @property
    def round(self):
        job, model = os.path.split(self.directory)
        match = re.search('round_(\d+)', job)
        return int(match.group(1)) if match else 1

    @property
    def name(self):
        job, model = os.path.split(self.directory)
        name = model

        match_06 = re.match(r'\w+\.(\d+)', model)
        match_08 = re.match(r'[A-Z]\d+[A-Z]', model)

        if match_06:
            name = match_06.group(1)
            if 'bad_pick' in job: name += '*'

        if match_08:
            name = model

        return name

    def remove_outlier(self, index):
        self.paths = delete(self.paths, index)
        self.scores = delete(self.scores, index)
        self.loop_rmsds = delete(self.loop_rmsds, index)
        self.cooh_dists = delete(self.cooh_dists, index, 0)

        self._save_scores_and_dists()


    notes = property(get_notes, set_notes)
    interest = property(get_interest, set_interest)
    rep = representative = property(get_representative, set_representative)
    representative_path = property(get_representative_path)
    fancy_path = property(get_fancy_path)

    def _load_annotations(self):
        try:
            with open(self.notes_path) as file:
                self._notes = file.read()
        except IOError:
            pass

        self._interest = os.path.exists(self.interest_path)

        try:
            with open(self.rep_path) as file:
                self._representative = int(file.read())
        except IOError:
            pass

    def _load_sequence(self):
        try:
            with open(self.sequence_path) as file:
                self.sequence = file.read().strip()

        except IOError:
            pdb_files = os.path.join(self.directory, '*.pdb.gz')
            pdb_file = sorted(glob.glob(pdb_files))[0]

            model = pdb.RosettaModel(pdb_file)
            self.sequence = model.sequence()
            self._save_sequence()

    def _load_scores_and_dists(self, use_cache):
        from libraries import distances

        records = distances.load(self.directory, use_cache)
        self.paths = records['path']
        self.scores = records['score']
        self.loop_rmsds = records['loop_dist']
        self.cooh_dists = records['restraint_dist']

    def _save_notes(self):
        with open(self.notes_path, 'w') as file:
            file.write(self.notes)

        if os.path.exists(self.notes_path) and not self.notes:
            os.remove(self.notes_path)

    def _save_interest(self):
        path_exists = os.path.exists(self.interest_path)

        if self.interest:
            if path_exists: pass
            else: open(self.interest_path, 'w').close()
        else:
            if path_exists: os.remove(self.interest_path)
            else: pass

    def _save_representative(self):
        if self._representative is not None:
            with open(self.rep_path, 'w') as file:
                file.write(str(self._representative))

        elif os.path.exists(self.rep_path):
            os.remove(self.rep_path)

    def _save_sequence(self):
        with open(self.sequence_path, 'w') as file:
            file.write(self.sequence + '\n')

    def _save_scores_and_dists(self):
        savez(self.cache_path,
              paths=self.paths,
              scores=self.scores,
              loop_rmsds=self.loop_rmsds,
              cooh_dists=self.cooh_dists)


class ModelView (gtk.Window):

    def __init__(self, designs, arguments):
        # Setup the parent class.
        gtk.Window.__init__(self)
        self.add_events(gtk.gdk.KEY_PRESS_MASK)
        self.connect('key-press-event', self.on_hotkey_press)

        # Setup the data members.
        self.designs = designs
        self.keys = list()
        self.filter = 'all' if not arguments['--interesting'] else 'interesting'
        self.selected_decoy = None
        self.xlim = arguments.get('--xlim')
        if self.xlim is not None:
            self.xlim = float(self.xlim)

        self.loop_metrics = "Loop RMSD",
        self.cooh_metrics = "COOH RMSD", "Max COOH Distance"
        self.distance_metrics = self.loop_metrics + self.cooh_metrics
        self.metric = "Max COOH Distance"

        # Setup the GUI.
        self.connect('destroy', lambda x: gtk.main_quit())
        self.set_default_size(int(1.618 * 529), 529)
        #self.set_border_width(5)

        design_viewer = self.setup_design_viewer()
        design_list = self.setup_design_list()
        menu_bar = self.setup_menu_bar()

        hbox = gtk.HBox()
        hbox.pack_start(design_list, expand=False, padding=3)
        hbox.pack_start(design_viewer, expand=True, padding=3)

        vbox = gtk.VBox()
        vbox.pack_start(menu_bar, expand=False)
        vbox.pack_start(hbox, expand=True, padding=3)

        self.add(vbox)
        self.update_everything()
        self.show_all()

    def get_interesting_designs(self):
        for design in self.designs.values():
            if design.interest:
                yield design

    def num_interesting_designs(self):
        count = 0
        for design in self.designs.values():
            count += 1 if design.interest else 0
        return count


    def setup_design_list(self):
        return self.setup_job_tree_view()

    def setup_design_viewer(self):
        plot = self.setup_score_vs_dist_plot()
        notes = self.setup_annotation_area()

        panes = gtk.VPaned()
        panes.add1(plot)
        panes.add2(notes)

        return panes

    def setup_menu_bar(self):
        # Create the file menu.

        file_config = [
                ("Save interesting paths",
                    lambda w: self.save_interesting_paths()),
                ("Save interesting funnels",
                    lambda w: self.save_interesting_funnels()),
                ("Save interesting pymol sessions",
                    lambda w: self.save_interesting_pymol_sessions()),
                (u"Save sub-0.6Å decoys",
                    lambda w: self.save_subangstrom_decoys()),
        ]
        file_submenu = gtk.Menu()

        for label, callback in file_config:
            item = gtk.MenuItem(label)
            item.connect('activate', callback)
            item.show()
            file_submenu.append(item)

        file_item = gtk.MenuItem("File")
        file_item.set_submenu(file_submenu)
        file_item.show()

        # Create the view menu.

        view_config = [
                "Show all designs", 
                "Show interesting designs",
                "Show interesting and annotated designs",
                "Show interesting and unannotated designs",
                "Show annotated designs",
                "Show uninteresting designs",
        ]
        view_submenu = gtk.Menu()
        group = None

        def on_pick_filter(widget, filter):
            self.filter_by(filter)

        for label in view_config:
            filter = ' '.join(label.split()[1:-1])
            item = gtk.MenuItem(label)
            item.connect('activate', on_pick_filter, filter)
            item.show()
            view_submenu.append(item)

        view_item = gtk.MenuItem("View");
        view_item.set_submenu(view_submenu)
        view_item.show()

        # Create and return the menu bar.

        menu_bar = gtk.MenuBar()
        menu_bar.append(file_item)
        menu_bar.append(view_item)

        return menu_bar

    def setup_job_tree_view(self):
        list_store = gtk.ListStore(str)

        text = gtk.CellRendererText()
        icon = gtk.CellRendererPixbuf()

        self.view = gtk.TreeView(list_store)
        self.view.set_model(list_store)
        self.view.set_rubber_banding(True)
        self.view.set_enable_search(False)
        #self.view.set_size_request(200, -1)

        columns = [
                ('Glu', 'glu_position'),
                ('Del', 'num_deletions'),
                ('Rd', 'round'),
                ('Name', 'name'),
        ]

        for index, parameters in enumerate(columns):
            title, attr = parameters

            def cell_data_func(column, cell, model, iter, attr):
                key = model.get_value(iter, 0)
                design = self.designs[key]
                text = getattr(design, attr)
                weight = 700 if design.interest else 400

                cell.set_property('text', text)
                cell.set_property('weight', weight)

            def sort_func(model, iter_1, iter_2, attr):
                key_1 = model.get_value(iter_1, 0)
                key_2 = model.get_value(iter_2, 0)
                design_1 = self.designs[key_1]
                design_2 = self.designs[key_2]
                value_1 = getattr(design_1, attr)
                value_2 = getattr(design_2, attr)
                return cmp(value_1, value_2)

            list_store.set_sort_func(index, sort_func, attr);

            column = gtk.TreeViewColumn(title, text)
            column.set_cell_data_func(text, cell_data_func, attr)
            column.set_sort_column_id(index)
            self.view.append_column(column)

        selector = self.view.get_selection()
        selector.connect("changed", self.on_select_designs)
        selector.set_mode(gtk.SELECTION_MULTIPLE)

        scroller = gtk.ScrolledWindow()
        scroller.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        scroller.add(self.view)

        frame = gtk.Frame()
        frame.add(scroller)

        return frame

    def setup_score_vs_dist_plot(self):
        figure = Figure(facecolor='#edecea')

        self.axes = figure.add_axes((0.15, 0.15, 0.75, 0.75))
        self.axes.set_ylabel('Score')

        self.canvas = ModelCanvas(figure)
        self.canvas.mpl_connect('pick_event', self.on_select_decoy)
        self.canvas.mpl_connect('button_press_event', self.on_click_plot_mpl)
        self.canvas.connect('button-press-event', self.on_click_plot_gtk)
        self.canvas.set_size_request(-1, 350)

        self.axis_menu = gtk.Menu()
        self.axis_menu_items = {
                x: gtk.CheckMenuItem(x) for x in self.distance_metrics}
        self.axis_menu_handlers = [
                (item, item.connect('toggled', self.on_change_metric))
                for item in self.axis_menu_items.values()]

        for item in self.axis_menu_items.values():
            self.axis_menu.append(item)
            item.set_draw_as_radio(True)
            item.show()

        self.toolbar = ModelToolbar(self.canvas, self, self.axis_menu)

        vbox = gtk.VBox()
        vbox.pack_start(self.canvas)
        vbox.pack_start(self.toolbar, expand=False)

        return vbox

    def setup_annotation_area(self):
        self.notes = gtk.TextView()
        self.notes.set_wrap_mode(gtk.WRAP_WORD)
        self.notes.set_size_request(-1, 100)
        self.notes.set_left_margin(3)
        self.notes.set_right_margin(3)
        self.notes.set_pixels_above_lines(3)
        self.notes.set_pixels_below_lines(3)
        self.notes.set_cursor_visible(True)
        self.notes.get_buffer().connect('changed', self.on_edit_annotation)

        scroll_window = gtk.ScrolledWindow()
        scroll_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scroll_window.add(self.notes)

        frame = gtk.Frame()
        frame.add(scroll_window)

        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_APPLY, gtk.ICON_SIZE_BUTTON)

        self.mark_as_interesting = gtk.ToggleButton()
        self.mark_as_interesting.add(image)
        self.mark_as_interesting.connect('toggled', self.on_mark_as_interesting)

        hbox = gtk.HBox()
        hbox.pack_start(frame)
        hbox.pack_start(self.mark_as_interesting, expand=False)

        return hbox


    def on_hotkey_press(self, widget, event):
        key = gtk.gdk.keyval_name(event.keyval).lower()
    
        hotkeys = {
                'tab': self.toggle_metrics,
                'escape': self.normal_mode,
        }
        
        normal_mode_hotkeys = {
                'j': self.next_design,      'f': self.next_design,
                'k': self.previous_design,  'd': self.previous_design,
                'i': self.insert_mode,      'a': self.insert_mode,
                'z': self.zoom_mode,
                'x': self.pan_mode,
                'c': self.refocus_plot,
                'space': self.toggle_interest,
        }

        if self.get_focus() is not self.notes:
            hotkeys.update(normal_mode_hotkeys)

        if key in hotkeys:
            hotkeys[key]()
            return True

    def on_toggle_filter(self, widget, key):
        if widget.get_active():
            self.filters.add(key)
        else:
            self.filters.discard(key)

        self.update_filter()

    def on_select_designs(self, selection) :
        new_keys = []
        old_keys = self.keys[:]
        self.keys = []
        model, paths = selection.get_selected_rows()

        for path in paths:
            iter = model.get_iter(path)
            key = model.get_value(iter, 0)
            new_keys.append(key)

        # Don't change the order of designs that were already selected.  The 
        # order affects how the color of the design in the score vs rmsd plot, 
        # and things get confusing if it changes.

        for key in old_keys:
            if key in new_keys:
                self.keys.append(key)

        for key in new_keys:
            if key not in self.keys:
                self.keys.append(key)

        # This is an efficiency thing.  The 'J' and 'K' hotkeys works in two 
        # steps: first unselect everything and then select the next row in 
        # order.  Redrawing the plot is expensive, so it's worthwhile to skip 
        # redrawing after that first step.

        if self.keys:
            self.update_plot()
            self.update_annotations()

    def on_select_decoy(self, event):
        self.selected_decoy = event.ind[0], event.artist.design

    def on_click_plot_mpl(self, event):
        if self.selected_decoy and event.button == 1:
            index, design = self.selected_decoy
            path = design.paths[index]
            self.toolbar.set_decoy(os.path.basename(path))

    def on_click_plot_gtk(self, widget, event):
        if event.button != 3: return
        if self.toolbar._active == 'PAN': return
        if self.toolbar._active == 'ZOOM': return
        if self.selected_decoy is None: return

        index, design = self.selected_decoy
        path = design.paths[index]
        is_rep = (design.representative == index)
        self.selected_decoy = None

        file_menu = gtk.Menu()

        import yaml

        # The following block is a recipe I copied off the web.  Somehow it 
        # gets YAML to parse the document in order into an OrderedDict.

        mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG
        def dict_representer(dumper, data):
            return dumper.represent_mapping(mapping_tag, data.iteritems())
        def dict_constructor(loader, node):
            return collections.OrderedDict(loader.construct_pairs(node))
        yaml.add_representer(collections.OrderedDict, dict_representer)
        yaml.add_constructor(mapping_tag, dict_constructor)

        with open('pymol_modes.txt') as file:
            pymol_modes = yaml.load(file)

        for key in pymol_modes:
            item = gtk.MenuItem(key)
            item.connect(
                    'activate', self.on_show_decoy_in_pymol,
                    design, index, pymol_modes)
            file_menu.append(item)

        edit_modes = gtk.MenuItem("Edit pymol configuration")
        edit_modes.connect('activate', lambda widget: self.edit_modes())

        copy_path = gtk.MenuItem("Copy path to decoy")
        copy_path.connect('activate', self.on_copy_decoy_path, path)

        if index == design.representative:
            choose_rep = gtk.MenuItem("Reset representative")
            choose_rep.connect(
                'activate', self.on_set_representative, design, None)
        else:
            choose_rep = gtk.MenuItem("Set as representative")
            choose_rep.connect(
                'activate', self.on_set_representative, design, index)

        remove_outlier = gtk.MenuItem("Remove outlier")
        remove_outlier.connect('activate', self.on_remove_outlier, design, index)

        file_menu.append(gtk.SeparatorMenuItem())
        file_menu.append(edit_modes)
        file_menu.append(copy_path)
        file_menu.append(choose_rep)
        file_menu.append(remove_outlier)
        file_menu.foreach(lambda item: item.show())
        file_menu.popup(None, None, None, event.button, event.time)

    def on_show_decoy_in_pymol(self, widget, design, decoy, configs):
        key = widget.get_label()
        open_in_pymol(design, decoy, configs[key])

    def on_copy_decoy_path(self, widget, path):
        import subprocess
        xsel = subprocess.Popen(['xsel', '-pi'], stdin=subprocess.PIPE)
        xsel.communicate(path)

    def on_set_representative(self, widget, design, index):
        design.set_representative(index)
        self.update_plot()

    def on_remove_outlier(self, widget, design, index):
        message = gtk.MessageDialog(
                type=gtk.MESSAGE_QUESTION,
                buttons=gtk.BUTTONS_OK_CANCEL)
        message.set_markup("Remove this outlier?")
        response = message.run()
        message.destroy()

        if response == gtk.RESPONSE_OK:
            design.remove_outlier(index)
            self.update_plot()

    def on_mark_as_interesting(self, widget):
        assert len(self.keys) == 1
        design = self.designs[self.keys[0]]
        interest = widget.get_active()
        design.set_interest(interest)
        self.view.queue_draw()

    def on_edit_annotation(self, buffer):
        assert len(self.keys) == 1
        design = self.designs[self.keys[0]]
        bounds = buffer.get_bounds()
        notes = buffer.get_text(*bounds)
        design.set_notes(notes)

    def on_change_metric(self, widget):
        self.update_metric(widget.get_label())


    def normal_mode(self):
        self.set_focus(None)

        if self.toolbar._active == 'PAN':
            self.toolbar.pan()

        if self.toolbar._active == 'ZOOM':
            self.toolbar.zoom()

        self.toolbar.unset_decoy()

    def insert_mode(self):
        self.set_focus(self.notes)

    def zoom_mode(self):
        self.toolbar.zoom()

    def pan_mode(self):
        self.toolbar.pan()

    def refocus_plot(self):
        self.toolbar.home()
        self.normal_mode()

    def filter_by(self, filter):
        self.filter = filter
        self.update_filter()

    def next_design(self):
        selection = self.view.get_selection()
        model, paths = selection.get_selected_rows()
        num_paths = model.iter_n_children(None)
        if paths[-1][0] < model.iter_n_children(None) - 1:
            for path in paths: selection.unselect_path(path)
            selection.select_path(paths[-1][0] + 1)
            self.view.scroll_to_cell(paths[-1][0] + 1)

    def previous_design(self):
        selection = self.view.get_selection()
        model, paths = selection.get_selected_rows()
        if paths[0][0] > 0:
            for path in paths: selection.unselect_path(path)
            selection.select_path(paths[0][0] - 1)
            self.view.scroll_to_cell(paths[0][0] - 1)

    def toggle_interest(self):
        current = self.mark_as_interesting.get_active()
        self.mark_as_interesting.set_active(not current)

    def toggle_metrics(self):
        if self.metric in self.cooh_metrics:
            self.update_metric("Loop RMSD")
        else:
            self.update_metric("Max COOH Distance")

    def edit_modes(self):
        import subprocess
        subprocess.call(('gvim', 'pymol_modes.txt'))

    def save_interesting_paths(self):
        chooser = gtk.FileChooserDialog(
                action=gtk.FILE_CHOOSER_ACTION_SAVE,
                buttons=(
                    gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    gtk.STOCK_OPEN, gtk.RESPONSE_OK))

        chooser.set_current_folder(os.getcwd())
        chooser.set_current_name('interesting_paths.txt')

        response = chooser.run()

        if response == gtk.RESPONSE_OK:
            with open(chooser.get_filename(), 'w') as file:
                file.writelines(
                        design.paths[design.representative] + '\n'
                        for design in self.get_interesting_designs())

        chooser.destroy()

    def save_interesting_funnels(self):
        from matplotlib.backends.backend_pdf import PdfPages
        import matplotlib.pyplot as plt

        chooser = gtk.FileChooserDialog(
                action=gtk.FILE_CHOOSER_ACTION_SAVE,
                buttons=(
                    gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    gtk.STOCK_OPEN, gtk.RESPONSE_OK))

        chooser.set_current_folder(os.getcwd())
        chooser.set_current_name('interesting_funnels.pdf')

        response = chooser.run()

        if response == gtk.RESPONSE_OK:
            pdf = PdfPages(chooser.get_filename())

            for index, design in enumerate(self.get_interesting_designs()):
                plt.figure(figsize=(8.5, 11))
                plt.suptitle(design.fancy_path)

                axes = plt.subplot(2, 1, 1)
                self.plot_score_vs_dist(axes, [design], metric="COOH RMSD")

                axes = plt.subplot(2, 1, 2)
                self.plot_score_vs_dist(axes, [design], metric="Loop RMSD")

                pdf.savefig(orientation='portrait')
                plt.close()

            pdf.close()

        chooser.destroy()

    def save_interesting_pymol_sessions(self):
        chooser = gtk.FileChooserDialog(
                action=gtk.FILE_CHOOSER_ACTION_SAVE,
                buttons=(
                    gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    gtk.STOCK_OPEN, gtk.RESPONSE_OK))

        chooser.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
        chooser.set_current_folder(os.getcwd())

        response = chooser.run()

        if response == gtk.RESPONSE_OK:
            directory = chooser.get_filename()

            with open('pymol_modes.txt') as file:
                base_config = yaml.load(file)['Evaluate decoy in pymol']

            for design in self.get_interesting_designs():
                decoy = design.representative
                config = base_config + '; save ' + os.path.join(
                        directory, design.get_fancy_path('.pse'))

                open_in_pymol(design, decoy, config, gui=False)

        chooser.destroy()

    def save_subangstrom_decoys(self):
        designs = [self.designs[k] for k in self.keys]

        for design in designs:
            job, outputs = os.path.split(design.directory)
            best_decoys = os.path.join(job, 'best_decoys')
            if os.path.exists(best_decoys): shutil.rmtree(best_decoys)
            os.mkdir(best_decoys)

        for design in designs:
            job, outputs = os.path.split(design.directory)
            best_decoys = os.path.join(job, 'best_decoys')

            distances = design.get_distances('Max COOH Distance')
            paths = array(design.paths)[distances < 0.6]

            for path in list(paths):
                id = os.path.basename(path)
                source = os.path.join('..', outputs, id)
                link_name = os.path.join(best_decoys, outputs + '.' + id)
                os.symlink(source, link_name)

    def plot_score_vs_dist(self, axes, designs, **kwargs):
        from graphics import tango
        from itertools import count

        labels = kwargs.get('labels', None)
        metric = kwargs.get('metric', self.metric)
        xlim = kwargs.get('xlim', self.xlim)
        ymin = inf

        axes.clear()
        axes.set_xlabel(metric)
        axes.set_ylabel('Score')
        
        for index, design in enumerate(designs):
            rep = design.representative
            distances = design.get_distances(metric)
            ymin = min(ymin, min(design.scores))
            color = tango.color_from_cycle(index)
            label = labels[index] if labels is not None else ''

            # Highlight the representative decoy.
            axes.scatter(
                    [distances[rep]], [design.scores[rep]],
                    s=60, c=tango.yellow[1], marker='o', edgecolor='none')

            # Draw the whole score vs distance plot.
            lines = axes.scatter(
                    distances, design.scores,
                    s=15, c=color, marker='o', edgecolor='none',
                    label=label, picker=True)

            lines.paths = design.paths
            lines.design = design

        axes.axvline(1, color='gray', linestyle='--')
        axes.set_ylim(bottom=ymin-2, top=ymin+20)

        if xlim is None:
            axes.set_xlim(0, 10 if metric == "Loop RMSD" else 25)
        else:
            axes.set_xlim(0, xlim)

        if labels and 1 < len(designs) < 5:
            axes.legend()


    def update_everything(self):
        self.update_filter()
        self.update_annotations()
        self.update_metric(self.metric)

    def update_metric(self, metric):
        for widget, id in self.axis_menu_handlers:
            widget.handler_block(id)

        self.axis_menu_items[self.metric].set_active(False)
        self.metric = metric
        self.axis_menu_items[self.metric].set_active(True)

        for widget, id in self.axis_menu_handlers:
            widget.handler_unblock(id)

        self.update_plot()

    def update_plot(self):
        designs = [self.designs[k] for k in self.keys]
        self.plot_score_vs_dist(self.axes, designs, labels=self.keys)
        self.toolbar.set_decoy("")
        self.canvas.draw()

    def update_annotations(self):
        if len(self.keys) == 1:
            design = self.designs[self.keys[0]]
            self.notes.get_buffer().set_text(design.notes)
            self.notes.set_sensitive(True)
            self.mark_as_interesting.set_active(design.interest)
            self.mark_as_interesting.set_sensitive(True)
        else:
            self.notes.set_sensitive(False)
            self.mark_as_interesting.set_sensitive(False)
        

    def update_filter(self):
        model = self.view.get_model()
        selector = self.view.get_selection()
        model.clear()

        for key in sorted(self.designs):
            design = self.designs[key]
            column = [key]

            if self.filter == 'all':
                model.append(column)

            elif self.filter == 'interesting':
                if design.interest:
                    model.append(column)

            elif self.filter == 'interesting and annotated':
                if design.interest and design.notes:
                    model.append(column)

            elif self.filter == 'interesting and unannotated':
                if design.interest and not design.notes:
                    model.append(column)

            elif self.filter == 'annotated':
                if design.notes:
                    model.append(column)

            elif self.filter == 'uninteresting':
                if not design.interest:
                    model.append(column)

            else:
                model.append(column)

        num_designs = model.iter_n_children(None)
        selector.select_path((0,))


class ModelCanvas (FigureCanvasGTKAgg):

    def __init__(self, figure):
        FigureCanvasGTKAgg.__init__(self, figure)

    def button_press_event(self, widget, event):
        FigureCanvasGTKAgg.button_press_event(self, widget, event)
        return False


class ModelToolbar (NavigationToolbar2GTKAgg):

    toolitems = ( # (fold)
        ('Home', 'Reset original view', 'home', 'home'),
        ('Back', 'Back to previous view', 'back', 'back'),
        ('Forward', 'Forward to next view', 'forward', 'forward'),
        (None, None, None, None),
        ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'),
        ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
        (None, None, None, None),
        ('Axis', 'Change the distance metric', 'subplots', 'configure_axis'),
        ('Save', 'Save the figure', 'filesave', 'save_figure'),
    )

    def __init__(self, canvas, parent, axis_menu):
        NavigationToolbar2GTKAgg.__init__(self, canvas, parent)
        self.axis_menu = axis_menu
        self.decoy_selected = False

    def configure_axis(self, button):
        self.axis_menu.popup(None, None, None, 0, 0)

    def set_decoy(self, message):
        self.decoy_selected = True
        NavigationToolbar2GTKAgg.set_message(self, message)

    def unset_decoy(self):
        self.decoy_selected = False
        self.set_message("")

    def set_message(self, message):
        if not self.decoy_selected:
            NavigationToolbar2GTKAgg.set_message(self, message)



def parse_designs(directories, use_cache=True):
    from os.path import join, isdir, dirname, basename

    designs = collections.OrderedDict()
    ignore = 'inputs', 'best_decoys', 'single_mutants', 'combined_mutants'

    for directory in directories:
        if isdir(directory) and basename(directory) not in ignore and os.listdir(directory):
            path = join(dirname(directory), 'inputs', 'labels.yaml')

            try:
                with open(path) as file:
                    labels = yaml.load(file)

                label = labels.get(basename(directory), basename(directory))
                key = os.path.join(dirname(directory), label)

            except IOError:
                key = directory

            designs[key] = Model(directory, use_cache)

    return designs

def find_cooh_distances(model, target, resi):
    from scipy.spatial.distance import euclidean
    
    residues = [
            model.select_chain('A').select_residues(resi),
            target.select_chain('A').select_residues(38)
    ]
    coohs = [None, None]
    oxygens = [None, None]
    carbons = [None, None]

    for i, residue in enumerate(residues):
        residue_type = residue.get_atom(0)['residue-name']

        if residue_type == 'glu':
            oxygens[i] = residue.select_atoms('OE1', 'OE2').coordinates
            carbons[i] = residue.select_atoms('CG').coordinates
        elif residue_type == 'asp':
            oxygens[i] = residue.select_atoms('OD1', 'OD2').coordinates
            carbons[i] = residue.select_atoms('CB').coordinates
        elif residue_type == 'asn':
            oxygens[i] = residue.select_atoms('OD1', 'ND2').coordinates
            carbons[i] = residue.select_atoms('CB').coordinates
        else:
            raise ValueError("Residue {} must be Glu, Asp, or Asn".format(resi))

        coohs[i] = vstack((oxygens[i], carbons[i]))
        assert coohs[i].shape == (3, 3)

    o1_o1 = euclidean(coohs[0][0], coohs[1][0])
    o2_o2 = euclidean(coohs[0][1], coohs[1][1])
    o1_o2 = euclidean(coohs[0][0], coohs[1][1])
    o2_o1 = euclidean(coohs[0][1], coohs[1][0])
    c_c   = euclidean(coohs[0][2], coohs[1][2])

    max_matched_dist = max(o1_o1, o2_o2)
    max_mismatched_dist = max(o1_o2, o2_o1)

    if max_matched_dist < max_mismatched_dist:
        return array((o1_o1, o2_o2, c_c))
    else:
        return array((o1_o2, o2_o1, c_c))

def open_in_pymol(design, decoy, config, gui=True):
    import subprocess

    path = design.paths[decoy]
    paths = path, 'data/original_structures/4UN3.pdb.gz'

    wt_name = '4UN3'
    design_name = os.path.basename(path)[:-len('.pdb.gz')]

    #job_target, decoy = os.path.split(path); decoy = decoy[:-len('.pdb.gz')]
    #job, target = os.path.split(job_target)
    #target_path = os.path.join(job, 'inputs', target + '.pdb.gz')
    #wt_path = os.path.join('..', 'structures', 'wt-lig-dimer.pdb')
    #paths = path, wt_path, target_path
    #design_name = design.fancy_path

    #glu_match = re.search('glu_(\d+)', path)
    #glu_position = int(glu_match.group(1)) if glu_match else 38

    #delete_match = re.search('delete_(\d+)', path)
    #num_deletions = int(delete_match.group(1)) if delete_match else 0

    #loop_name = 'delete_{}.glu_{}'.format(num_deletions, glu_position)

    #resfile = os.path.join('..', '05.fixbb_design', loop_name + '.res')
    #loop_file = os.path.join(job, 'loops.dat')

    #with open(loop_file) as file:
    #    fields = file.read().split()
    #    loop_start = int(fields[1])
    #    loop_stop = int(fields[2])
    
    config = config.format(**locals())

    if gui:
        pymol_command = ('pymol', '-qx') + paths + ('-d', config)
    else:
        pymol_command = ('pymol', '-c') + paths + ('-d', config)

    with open(os.devnull, 'w') as devnull:
        subprocess.Popen(pymol_command, stdout=devnull)


if __name__ == '__main__':
    arguments = docopt.docopt(__doc__)
    directories = arguments['<directories>']
    use_cache = not arguments['--force']
    designs = parse_designs(directories, use_cache)

    if not arguments['--quiet']:
        gui = ModelView(designs, arguments)
        if not os.fork(): gtk.main()
