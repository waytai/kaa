import kaa
import kaa.log
from kaa.command import Commands, command, is_enable, norec, norerun
from kaa.ui.msgbox import msgboxmode

class FileCommands(Commands):
    @command('file.new')
    @norec
    @norerun
    def file_new(self, wnd):
        from kaa import fileio
        doc = fileio.newfile()
        kaa.app.show_doc(doc)

    @command('file.open')
    @norec
    @norerun
    def file_open(self, wnd):
        def cb(filename, encoding, newline):
            for frame in kaa.app.get_frames():
                for doc in frame.get_documents():
                    if doc.get_filename() == filename:
                        if doc.wnds:
                            wnd = doc.wnds[0]
                            wnd.get_label('frame').bring_top()
                            wnd.activate()

                        MAX_FILENAMEMSG_LEN = 50
                        if len(filename) > MAX_FILENAMEMSG_LEN:
                            filename = '...{}'.format(filename[MAX_FILENAMEMSG_LEN*-1:])

                        kaa.app.messagebar.set_message("`{}` is already opened.".format(filename))
                        return

            doc = kaa.app.storage.openfile(filename, encoding, newline)
            kaa.app.show_doc(doc)

        from kaa.ui.selectfile import selectfile
        selectfile.show_fileopen('.', cb)

    @command('file.info')
    @norec
    @norerun
    def file_info(self, wnd):
        from kaa.ui.fileinfo import fileinfomode
        fileinfomode.show_fileinfo(wnd)

    @command('file.save')
    @norec
    @norerun
    def file_save(self, wnd, filename=None, saved=None, document=None,
                  encoding=None, newline=None):
        "Save document"
        try:
            if not document:
                document=wnd.document
            if not filename and document.fileinfo:
                filename = document.fileinfo.fullpathname

            if encoding:
                document.fileinfo.encoding = encoding
            if newline:
                document.fileinfo.newline = newline

            if filename:
                kaa.app.storage.save_document(filename, document)
                # notify file saved
                if saved:
                    saved()
            else:
                # no file name. Show save_as dialog.
                self.file_saveas(wnd, saved=saved, document=document)

        except Exception as e:
            kaa.log.exception('File write error:')
            msgboxmode.MsgBoxMode.show_msgbox(
                'File write error: '+str(e), ['&Ok'],
                lambda c:self.file_saveas(wnd),
                keys=['\r', '\n'])

    @command('file.saveas')
    @norec
    @norerun
    def file_saveas(self, wnd, saved=None, document=None):
        "Show save_as dialog and save to the specified file."
        def cb(filename, enc, newline):
            self.file_save(wnd, filename, saved=saved, document=document,
                           encoding=enc, newline=newline)

        if not document:
            document = wnd.document

        from kaa.ui.selectfile import selectfile
        selectfile.show_filesaveas(document.fileinfo.fullpathname,
                                        document.fileinfo.newline,
                                        document.fileinfo.encoding, cb)

    def ask_doc_close(self, wnd, document, callback, msg):
        def saved():
           callback()

        def choice(c):
            if c == 'y':
                self.file_save(wnd, saved=saved, document=document)
            elif c == 'n':
                callback()

        if document.undo and document.undo.is_dirty():
            msgboxmode.MsgBoxMode.show_msgbox(
                '{} [{}]: '.format(
                    msg, document.get_title()),
                ['&Yes', '&No', '&Cancel'], choice)
        else:
            callback()

    def save_documents(self, wnd, docs, callback, msg='', force=False):

        docs = list(docs)
        def _save_documents():
            if not docs:
                if callback:
                    callback()
            else:
                doc = docs.pop()
                if force:
                    self.file_save(wnd, saved=_save_documents, document=doc)
                else:
                    self.ask_doc_close(wnd, doc, _save_documents, msg)

        _save_documents()

    @command('file.close')
    @norec
    @norerun
    def file_close(self, wnd):
        "Close active frame"

        import kaa.fileio

        frame = wnd.get_label('frame')
        editors = {e for e in frame.get_editors()}
        alldocs = {e.document for e in editors}

        docs = []
        for doc in alldocs:
            doc_editors = set(doc.wnds) - editors
            if not doc_editors:
                docs.append(doc)

        def saved():
            frame.destroy()

            if frame.mainframe.childframes:
                kaa.app.set_focus(frame.mainframe.childframes[-1])
            else:
                doc = kaa.fileio.newfile(provisional=True)
                kaa.app.show_doc(doc)

        self.save_documents(wnd, docs, saved, 'Save file before close?')

    def get_current_documents(self, wnd):
        docs = set()
        for frame in wnd.mainframe.childframes:
            editors = {e for e in frame.get_editors()}
            docs |= {e.document for e in editors if e.document.mode.DOCUMENT}
        return docs
        
    @command('file.save.all')
    @norec
    @norerun
    def file_saveall(self, wnd):

        def saved():
            pass
        
        docs = self.get_current_documents(wnd)
        docs = [doc for doc in docs if doc.undo.is_dirty()]
        if docs:
            self.save_documents(wnd, docs, saved, force=True)

    @command('file.quit')
    @norec
    @norerun
    def file_quit(self, wnd):

        def saved():
            kaa.app.quit()
        
        docs = self.get_current_documents(wnd)
        self.save_documents(wnd, docs, saved, 'Save file before close?')
