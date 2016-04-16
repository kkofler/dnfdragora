
'''
dnfdragora is a graphical frontend based on rpmdragora implementation
that uses dnf as rpm backend, due to libyui python bindings dnfdragora
is able to comfortably behave like a native gtk or qt5 or ncurses application

License: GPLv3

Author:  Andelo Naselli <anaselli@linux.it>

@package dnfdragora
'''

import os
import sys
import platform
import yui

import dnfdragora.dnfbase as dnfbase
import dnfdragora.groupicons as groupicons
import dnfdragora.progress_ui as progress_ui

#################
# class mainGui #
#################
class mainGui():
    """
    Main class
    """

    def __init__(self, options={}):

        self.options = options
        self.toRemove = []
        self.toInstall = []
        self.itemList = {}
        # {
        #   name-epoch_version-release.arch : { pkg: dnf-pkg, item: YItem}
        # }
        self.groupList = {}
        # {
        #    localized_name = { "item" : item, "name" : groupName }
        # }

        yui.YUI.app().setApplicationTitle("Software Management - dnfdragora")
        #TODO fix icons
        wm_icon = "/usr/share/icons/rpmdrake.png"
        yui.YUI.app().setApplicationIcon(wm_icon)

        MGAPlugin = "mga"

        self.factory = yui.YUI.widgetFactory()
        mgaFact = yui.YExternalWidgets.externalWidgetFactory(MGAPlugin)
        self.mgaFactory = yui.YMGAWidgetFactory.getYMGAWidgetFactory(mgaFact)
        self.optFactory = yui.YUI.optionalWidgetFactory()

        ### MAIN DIALOG ###
        self.dialog = self.factory.createMainDialog()

        vbox = self.factory.createVBox(self.dialog)

        hbox_headbar = self.factory.createHBox(vbox)
        head_align_left = self.factory.createLeft(hbox_headbar)
        head_align_right = self.factory.createRight(hbox_headbar)
        headbar = self.factory.createHBox(head_align_left)
        headRight = self.factory.createHBox(head_align_right)

        #Line for logo and title
        hbox_iconbar  = self.factory.createHBox(vbox)
        head_align_left  = self.factory.createLeft(hbox_iconbar)
        hbox_iconbar     = self.factory.createHBox(head_align_left)
        self.factory.createImage(hbox_iconbar, wm_icon)

        self.factory.createHeading(hbox_iconbar, "Software Management")

        hbox_top = self.factory.createHBox(vbox)
        hbox_middle = self.factory.createHBox(vbox)
        hbox_bottom = self.factory.createHBox(vbox)
        hbox_footbar = self.factory.createHBox(vbox)

        hbox_headbar.setWeight(1,10)
        hbox_top.setWeight(1,10)
        hbox_middle.setWeight(1,50)
        hbox_bottom.setWeight(1,30)
        hbox_footbar.setWeight(1,10)

        # Tree for groups
        self.tree = self.factory.createTree(hbox_middle, "")
        self.tree.setWeight(0,20)
        self.tree.setNotify(True)

        packageList_header = yui.YTableHeader()
        columns = [ 'Name', 'Summary', 'Version', 'Release', 'Arch']

        packageList_header.addColumn("")
        for col in (columns):
            packageList_header.addColumn(col)

        packageList_header.addColumn("Status")

        self.packageList = self.mgaFactory.createCBTable(hbox_middle,packageList_header,yui.YCBTableCheckBoxOnFirstColumn)
        self.packageList.setWeight(0,50)
        self.packageList.setImmediateMode(True)

        self.filters = {
            'all' : {'title' : "All"},
            'installed' : {'title' : "Installed"},
            'not_installed' : {'title' : "Not installed"}
        }
        ordered_filters = [ 'all', 'installed', 'not_installed' ]
        if platform.machine() == "x86_64" :
            # NOTE this should work on other architectures too, but maybe it
            #      is a nonsense, at least for i586
            self.filters['skip_other'] = {'title' : "Show %s and noarch only" % platform.machine()}
            ordered_filters.append('skip_other')

        # TODO add backports
        self.views = {
            'all' : {'title' : "All"},
            'meta_pkgs' : {'title' : "Meta packages"},
            'gui_pkgs' : {'title' : "Packages with GUI"},
            'all_updates' : {'title' : "All updates"},
            'security' : {'title' : "Security updates"},
            'bugfix' : {'title' : "Bugfixes updates"},
            'normal' : {'title' : "General updates"}
        }
        ordered_views = [ 'all', 'meta_pkgs', 'gui_pkgs', 'all_updates', 'security', 'bugfix', 'normal']

        self.view_box = self.factory.createComboBox(hbox_top,"")
        itemColl = yui.YItemCollection()

        for v in ordered_views:
            item = yui.YItem(self.views[v]['title'], False)
            # adding item to views to find the item selected
            self.views[v]['item'] = item
            itemColl.push_back(item)
            item.this.own(False)

        self.view_box.addItems(itemColl)
        self.view_box.setNotify(True)

        self.filter_box = self.factory.createComboBox(hbox_top,"")
        itemColl.clear()

        for f in ordered_filters:
            item = yui.YItem(self.filters[f]['title'], False)
            # adding item to filters to find the item selected
            self.filters[f]['item'] = item
            itemColl.push_back(item)
            item.this.own(False)

        self.filter_box.addItems(itemColl)
        self.filter_box.setNotify(True)

        self.local_search_types = {
            'name'       : {'title' : "in names"       },
            'description': {'title' : "in descriptions"},
            'summary'    : {'title' : "in summaries"   },
            'file'       : {'title' : "in file names"  }
        }
        search_types = ['name', 'description', 'summary', 'file' ]

        self.search_list = self.factory.createComboBox(hbox_top,"")
        itemColl.clear()
        for s in search_types:
            item = yui.YItem(self.local_search_types[s]['title'], False)
            if s == search_types[0] :
                item.setSelected(True)
            # adding item to local_search_types to find the item selected
            self.local_search_types[s]['item'] = item
            itemColl.push_back(item)
            item.this.own(False)

        self.search_list.addItems(itemColl)
        self.search_list.setNotify(True)

        self.find_entry = self.factory.createInputField(hbox_top, "")

        #TODO icon_file = File::ShareDir::dist_file(ManaTools::Shared::distName(), "images/manalog.png")
        icon_file = ""
        self.find_button = self.factory.createIconButton(hbox_top, icon_file, "&Search")
        self.find_button.setWeight(0,6)
        self.dialog.setDefaultButton(self.find_button)
        self.find_entry.setKeyboardFocus()

        #TODO icon_file = File::ShareDir::dist_file(ManaTools::Shared::distName(), "images/rpmdragora/clear_22x22.png");
        self.reset_search_button = self.factory.createIconButton(hbox_top, icon_file, "&Reset")
        self.reset_search_button.setWeight(0,7)
        self.find_entry.setWeight(0,10)

        self.info = self.factory.createRichText(hbox_bottom,"Test")
        self.info.setWeight(0,40)
        self.info.setWeight(1,40);

        self.applyButton = self.factory.createIconButton(hbox_footbar,"","&Apply")
        self.applyButton.setWeight(0,6)

        self.quitButton = self.factory.createIconButton(hbox_footbar,"","&Quit")
        self.quitButton.setWeight(0,6)

        self.dnf = dnfbase.DnfBase()
        self.dialog.pollEvent();
        self._fillGroupTree()
        sel = self.tree.selectedItem()
        group = None
        if sel :
            group = self._groupNameFromItem(self.groupList, sel)

        filter = self._filterNameSelected()
        self._fillPackageList(group, filter)
        sel = self.packageList.toCBYTableItem(self.packageList.selectedItem())
        if sel :
            pkg_name = sel.cell(0).label()
            self.setInfoOnWidget(pkg_name)

    def _pkg_name(self, name, epoch, version, release, arch) :
        '''
            return a package name in the form name-epoch_version-release.arch
        '''
        return ("{0}-{1}_{2}-{3}.{4}".format(name, epoch, version, release, arch))

    def _fillPackageList(self, groupName=None, filter="all") :
        '''
        fill package list filtered by group if groupName is given,
        and checks installed packages.
        Special value for groupName 'All' means all packages
        Available filters are:
        all, installed, not_installed and skip_other
        '''

        yui.YUI.app().busyCursor()
        packages = self.dnf.packages

        self.itemList = {}
        # {
        #   name-epoch_version-release.arch : { pkg: dnf-pkg, item: YItem}
        # }
        v = []
        # Package API doc: http://dnf.readthedocs.org/en/latest/api_package.html
        for pkg in packages.installed :
            if groupName and (groupName == pkg.group or groupName == 'All') :
                if filter == 'all' or filter == 'installed' or (filter == 'skip_other' and (pkg.arch == 'noarch' or pkg.arch == platform.machine())) :
                    item = yui.YCBTableItem(pkg.name , pkg.summary , pkg.version, pkg.release, pkg.arch)
                    item.check(True)
                    self.itemList[self._pkg_name(pkg.name , pkg.epoch , pkg.version, pkg.release, pkg.arch)] = {
                        'pkg' : pkg, 'item' : item
                        }
                    item.this.own(False)

        # Package API doc: http://dnf.readthedocs.org/en/latest/api_package.html
        for pkg in packages.available:
            if groupName and (groupName == pkg.group or groupName == 'All') :
                if filter == 'all' or filter == 'not_installed' or (filter == 'skip_other' and (pkg.arch == 'noarch' or pkg.arch == platform.machine())) :
                    item = yui.YCBTableItem(pkg.name , pkg.summary , pkg.version, pkg.release, pkg.arch)
                    self.itemList[self._pkg_name(pkg.name , pkg.epoch , pkg.version, pkg.release, pkg.arch)] = {
                        'pkg' : pkg, 'item' : item
                        }
                    item.this.own(False)

        keylist = sorted(self.itemList.keys())

        for key in keylist :
            item = self.itemList[key]['item']
            v.append(item)

        #NOTE workaround to get YItemCollection working in python
        itemCollection = yui.YItemCollection(v)

        self.packageList.startMultipleChanges()
        # cleanup old changed items since we are removing all of them
        self.packageList.setChangedItem(None)
        self.packageList.deleteAllItems()
        self.packageList.addItems(itemCollection)
        self.packageList.doneMultipleChanges()

        yui.YUI.app().normalCursor()

    def _filterNameSelected(self) :
        '''
        return the filter name index from the selected filter
        '''
        filter = 'all'
        sel = self.filter_box.selectedItem()
        if sel:
            for k in self.filters.keys():
                if self.filters[k]['item'] == sel:
                    return k

        return filter

    def _groupNameFromItem(self, group, treeItem) :
        '''
        return the group name to be used for a search by group
        '''
        # TODO check type yui.YTreeItem?
        for g in group.keys() :
            if g == 'name' or g == 'item' :
                continue
            if group[g]['item'] == treeItem :
                return group[g]['name']
            elif group[g]['item'].hasChildren():
                gName =  self._groupNameFromItem(group[g], treeItem)
                if gName :
                    return gName

        return None


    def _fillGroupTree(self) :
        '''
        fill the group tree, look for the retrieved groups and set their icons
        from groupicons module
        '''

        self.groupList = {}
        rpm_groups = {}
        yui.YUI.app().busyCursor()
        packages = self.dnf.packages
        for pkg in packages.all:
            if not pkg.group in rpm_groups:
                rpm_groups[pkg.group] = 1

        rpm_groups = sorted(rpm_groups.keys())
        icon_path = self.options['icon_path'] if 'icon_path' in self.options.keys() else None
        gIcons = groupicons.GroupIcons(icon_path)
        groups = gIcons.groups()

        for g in rpm_groups:
            #X/Y/Z/...
            currG = groups
            currT = self.groupList
            subGroups = g.split("/")
            currItem = None
            parentItem = None
            groupName = None

            for sg in subGroups:
                if groupName:
                    groupName += "/%s"%(sg)
                else:
                    groupName = sg
                icon = gIcons.icon(groupName)

                if sg in currG:
                    currG = currG[sg]
                    if currG["title"] in currT :
                        currT = currT[currG["title"]]
                        parentItem = currT["item"]
                    else :
                        # create the item
                        item = None
                        if parentItem:
                            item = yui.YTreeItem(parentItem, currG["title"], icon)
                        else :
                            item = yui.YTreeItem(currG["title"], icon)
                        item.this.own(False)
                        currT[currG["title"]] = { "item" : item, "name" : groupName }
                        currT = currT[currG["title"]]
                        parentItem = item
                else:
                    # group is not in our group definition, but it's into the repository
                    # we just use it
                    if sg in currT :
                        currT = currT[sg]
                        parentItem = currT["item"]
                    else :
                        item = None
                        if parentItem:
                            item = yui.YTreeItem(parentItem, sg, icon)
                        else :
                            item = yui.YTreeItem(sg, icon)
                        item.this.own(False)
                        currT[sg] = { "item" : item, "name": groupName }
                        currT = currT[sg]
                        parentItem = item

        keylist = sorted(self.groupList.keys())
        v = []
        for key in keylist :
            item = self.groupList[key]['item']
            v.append(item)

        itemCollection = yui.YItemCollection(v)
        self.tree.startMultipleChanges()
        self.tree.deleteAllItems()
        self.tree.addItems(itemCollection)
        self.tree.doneMultipleChanges()
        yui.YUI.app().normalCursor()


    def setInfoOnWidget(self, pkg_name) :
        """
        write package description into info widget,
        this method performs a new query based on package name,
        future implementation could save package info into a temporary
        object structure linked to the selected item
        """
        packages = self.dnf.packages
        packages.all
        q = packages.query
        p_list = q.filter(name = pkg_name)
        self.info.setValue("")
        if (len(p_list)) :
            # NOTE first item of the list should be enough, different
            # arch should have same description for the package
            pkg = p_list[0]
            if pkg :
                s = "<h2> %s - %s </h2>%s" %(pkg.name, pkg.summary, pkg.description)
                self.info.setValue(s)

    def _searchPackages(self, filter='all', createTreeItem=False) :
        '''
        retrieves the info from search input field and from the search type list
        to perform a paclage research and to fill the package list widget

        return False if an empty string used
        '''
        #clean up tree
        if createTreeItem:
            self._fillGroupTree()

        search_string = self.find_entry.value()
        if search_string :
            fields = []
            type_item = self.search_list.selectedItem()
            for field in self.local_search_types.keys():
                if self.local_search_types[field]['item'] == type_item:
                    fields.append(field)
                    break

            yui.YUI.app().busyCursor()
            strings = search_string.split(" ,|:;")
            packages = self.dnf.search(fields, strings)


            self.itemList = {}
            # {
            #   name-epoch_version-release.arch : { pkg: dnf-pkg, item: YItem}
            # }

            # Package API doc: http://dnf.readthedocs.org/en/latest/api_package.html
            for pkg in packages:
                if (filter == 'all' or (filter == 'installed' and pkg.installed) or
                    (filter == 'not_installed' and not pkg.installed) or
                    (filter == 'skip_other' and (pkg.arch == 'noarch' or pkg.arch == platform.machine()))) :
                    item = yui.YCBTableItem(pkg.name , pkg.summary , pkg.version, pkg.release, pkg.arch)
                    item.check(pkg.installed)
                    self.itemList[self._pkg_name(pkg.name , pkg.epoch , pkg.version, pkg.release, pkg.arch)] = {
                        'pkg' : pkg, 'item' : item
                        }
                    item.this.own(False)

            keylist = sorted(self.itemList.keys())
            v = []
            for key in keylist :
                item = self.itemList[key]['item']
                v.append(item)

            itemCollection = yui.YItemCollection(v)

            self.packageList.startMultipleChanges()
            # cleanup old changed items since we are removing all of them
            self.packageList.setChangedItem(None)
            self.packageList.deleteAllItems()
            self.packageList.addItems(itemCollection)
            self.packageList.doneMultipleChanges()

            if createTreeItem:
                self.tree.startMultipleChanges()
                icon_path = self.options['icon_path'] if 'icon_path' in self.options.keys() else None
                gIcons = groupicons.GroupIcons(icon_path)
                icon = gIcons.icon("Search")
                treeItem = yui.YTreeItem(gIcons.groups()['Search']['title'] , icon, False)
                treeItem.setSelected(True)
                self.groupList[gIcons.groups()['Search']['title']] = { "item" : treeItem, "name" : "Search" }
                self.tree.addItem(treeItem)
                self.tree.rebuildTree()
                self.tree.doneMultipleChanges()
            yui.YUI.app().normalCursor()
        else :
            return False

        return True


    def handleevent(self):
        """
        Event-handler for the maindialog
        """
        while True:

            event = self.dialog.waitForEvent()

            eventType = event.eventType()

            rebuild_package_list = False
            group = None
            #event type checking
            if (eventType == yui.YEvent.CancelEvent) :
                break
            elif (eventType == yui.YEvent.WidgetEvent) :
                # widget selected
                widget  = event.widget()
                if (widget == self.quitButton) :
                    #### QUIT
                    break
                elif (widget == self.packageList) :
                    wEvent = yui.toYWidgetEvent(event)
                    if (wEvent.reason() == yui.YEvent.ValueChanged) :
                        changedItem = self.packageList.changedItem()
                        if changedItem :
                            pkg_name = changedItem.cell(0).label()
                            if changedItem.checked():
                                self.dnf.install(pkg_name)
                            else:
                                self.dnf.remove(pkg_name)

                        print("TODO checked, managing also version and arch\n")

                elif (widget == self.reset_search_button) :
                    #### RESET
                    rebuild_package_list = True
                    self.find_entry.setValue("")
                    self._fillGroupTree()

                elif (widget == self.find_button) :
                    #### FIND
                    filter = self._filterNameSelected()
                    if not self._searchPackages(filter, True) :
                        rebuild_package_list = True

                elif (widget == self.applyButton) :
                    #### APPLY
                    if os.getuid() == 0:
                        progress = progress_ui.Progress()
                        self.dnf.apply_transaction(progress)
                        self.dnf.fill_sack() # refresh the sack
                        # NOTE removing progress bar to make this Dialog the top most again
                        del progress
                        # TODO next line works better but installing and then removing or viceversa
                        #      crashes anyway
                        #self.dnf = dnfbase.DnfBase()
                        sel = self.tree.selectedItem()
                        if sel :
                            group = self._groupNameFromItem(self.groupList, sel)
                            if (group == "Search"):
                                filter = self._filterNameSelected()
                                if not self._searchPackages(filter) :
                                    rebuild_package_list = True
                            else:
                                rebuild_package_list = True
                    else:
                        # TODO use a dialog instead
                        print("You must be root to apply changes")

                elif (widget == self.tree) or (widget == self.filter_box) :
                    sel = self.tree.selectedItem()
                    if sel :
                        group = self._groupNameFromItem(self.groupList, sel)
                        if (group == "Search"):
                            filter = self._filterNameSelected()
                            if not self._searchPackages(filter) :
                                rebuild_package_list = True
                        else:
                            rebuild_package_list = True
                else:
                    print("Unmanaged widget")
            else:
                print("Unmanaged event")

            if rebuild_package_list :
                sel = self.tree.selectedItem()
                if sel :
                    group = self._groupNameFromItem(self.groupList, sel)
                    filter = self._filterNameSelected()
                    self._fillPackageList(group, filter)

            sel = self.packageList.toCBYTableItem(self.packageList.selectedItem())
            if sel :
                pkg_name = sel.cell(0).label()
                self.setInfoOnWidget(pkg_name)



        self.dialog.destroy()