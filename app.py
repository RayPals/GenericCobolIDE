import sys
import os
import subprocess
from typing import Optional


from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QMessageBox,
    QPlainTextEdit,
    QWidget,
    QVBoxLayout
)
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QKeySequence
from PyQt6.QtCore import QRegularExpression, Qt


class CobolHighlighter(QSyntaxHighlighter):
    """
    Syntax highlighter for COBOL language using QRegularExpression.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # Define COBOL keywords
        keywords = [
            'ACCEPT', 'ADD', 'CALL', 'CANCEL', 'COMPUTE', 'CONTINUE',
            'DELETE', 'DISPLAY', 'DIVIDE', 'ELSE', 'END-CALL', 'END-IF',
            'EVALUATE', 'GO', 'IF', 'INITIALIZE', 'INSPECT', 'MOVE',
            'MULTIPLY', 'OPEN', 'PERFORM', 'READ', 'REPLACE', 'RETURN',
            'REWRITE', 'SEARCH', 'STOP', 'STRING', 'SUBTRACT', 'UNSTRING',
            'WRITE'
        ]

        # Define formatting for keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("blue"))
        keyword_format.setFontWeight(QFont.Weight.Bold)

        # Create a list of tuples (pattern, format)
        self.highlighting_rules = []
        for word in keywords:
            pattern = QRegularExpression(r'\b{}\b'.format(word))
            self.highlighting_rules.append((pattern, keyword_format))

        # Define string literals
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("magenta"))
        string_patterns = [
            QRegularExpression(r'".*?"'),
            QRegularExpression(r"'.*?'")
        ]
        for pattern in string_patterns:
            self.highlighting_rules.append((pattern, string_format))

        # Define comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("green"))
        comment_pattern = QRegularExpression(r'^\s*\*>.*')
        self.highlighting_rules.append((comment_pattern, comment_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                start = match.capturedStart()
                length = match.capturedLength()
                self.setFormat(start, length, fmt)
        self.setCurrentBlockState(0)


class CobolIDE(QMainWindow):
    """
    A simple PyQt6-based IDE for editing and compiling COBOL code with GnuCOBOL.
    """
    def __init__(self) -> None:
        super().__init__()
        self.current_file: Optional[str] = None  # Track the currently open file path
        self._setup_ui()

    def _setup_ui(self) -> None:
        """
        Create and configure the main window's UI elements.
        """
        self.setWindowTitle("GNU Cobol IDE")
        self.setGeometry(100, 100, 900, 700)

        # === Central Widget & Layout =====================================
        central_widget = QWidget(self)
        main_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        # === Editor (QPlainTextEdit with Monospaced Font) ================
        self.editor = QPlainTextEdit(self)
        self.editor.setFont(QFont("Courier", 11))
        main_layout.addWidget(self.editor)

        # === Syntax Highlighter ============================================
        self.highlighter = CobolHighlighter(self.editor.document())

        # === Status Bar ==================================================
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

        # === Menu Bar and Actions ========================================
        self._create_actions()
        self._create_menus()

    # --------------------------------------------------------------------
    #  MENU / ACTIONS
    # --------------------------------------------------------------------
    def _create_actions(self) -> None:
        """
        Create actions for 'File' and 'Compile' menu items.
        """
        self.action_new = QAction("New", self)
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.triggered.connect(self.handle_new_file)

        self.action_open = QAction("Open...", self)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.triggered.connect(self.handle_open_file)

        self.action_save = QAction("Save", self)
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save.triggered.connect(self.handle_save_file)

        self.action_save_as = QAction("Save As...", self)
        self.action_save_as.triggered.connect(self.handle_save_file_as)

        self.action_compile = QAction("Compile", self)
        self.action_compile.setShortcut(QKeySequence(Qt.Key.Key_F5))
        self.action_compile.triggered.connect(self.handle_compile_cobol)

        self.action_exit = QAction("Exit", self)
        self.action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_exit.triggered.connect(self.close)

    def _create_menus(self) -> None:
        """
        Create the menu bar and add the actions to the 'File' menu.
        """
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(self.action_new)
        file_menu.addAction(self.action_open)
        file_menu.addAction(self.action_save)
        file_menu.addAction(self.action_save_as)
        file_menu.addSeparator()
        file_menu.addAction(self.action_compile)
        file_menu.addSeparator()
        file_menu.addAction(self.action_exit)

    # --------------------------------------------------------------------
    #  FILE HANDLING
    # --------------------------------------------------------------------
    def handle_new_file(self) -> None:
        """
        Create a new file. Prompt the user to save if the current file has unsaved changes.
        """
        if self._document_is_modified():
            if not self._prompt_save_discard_cancel("Do you want to save before creating a new file?"):
                return

        self.editor.clear()
        self.current_file = None
        self._update_window_title()
        self.status_bar.showMessage("New file created", 5000)

    def handle_open_file(self) -> None:
        """
        Open an existing file. Prompt the user to save if there are unsaved changes.
        """
        if self._document_is_modified():
            if not self._prompt_save_discard_cancel("Do you want to save before opening a new file?"):
                return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open COBOL File",
            "",
            "COBOL Files (*.cbl *.cob *.cpy);;All Files (*)"
        )
        if file_path:
            self._open_file(file_path)

    def handle_save_file(self) -> None:
        """
        Save the current file. If none is open, prompt the user for a file name.
        """
        if not self.current_file:
            self.handle_save_file_as()
        else:
            self._save_to_path(self.current_file)

    def handle_save_file_as(self) -> None:
        """
        Prompt the user to pick a file name to save the current content.
        """
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save As",
            "",
            "COBOL Files (*.cbl *.cob *.cpy);;All Files (*)"
        )
        if file_path:
            self._save_to_path(file_path)

    # --------------------------------------------------------------------
    #  COMPILATION
    # --------------------------------------------------------------------
    def handle_compile_cobol(self) -> None:
        """
        Compile the current file with GnuCOBOL (cobc). Prompts for an output executable path.
        """
        if not self.current_file:
            QMessageBox.warning(self, "Warning", "Please save the file before compiling.")
            return

        exe_path, _ = QFileDialog.getSaveFileName(
            self,
            "Compile to Executable",
            "",
            "Executable Files (*.exe);;All Files (*)"
        )
        if not exe_path:
            return

        # Determine GNUBASE and set environment variables
        gnubase = os.environ.get('GNUBASE')

        if not gnubase:
            # Attempt to set GNUBASE based on typical installation paths
            if sys.platform.startswith('win'):
                gnubase = r"C:\GnuCOBOL"  # Update as per your installation
            elif sys.platform.startswith('darwin') or sys.platform.startswith('linux'):
                gnubase = "/usr/local"  # Update as per your installation
            else:
                QMessageBox.critical(
                    self,
                    "Configuration Error",
                    "Unsupported operating system or GNUBASE not set."
                )
                return

        # Update environment variables for subprocess
        env = os.environ.copy()
        env['GNUBASE'] = gnubase
        env['COBPATH'] = os.path.join(gnubase, "lib", "gnucobol") + os.pathsep + \
                          os.path.join(gnubase, "lib", "cobc") + os.pathsep + \
                          env.get('COBPATH', '')
        env['PATH'] = os.path.join(gnubase, "bin") + os.pathsep + env.get('PATH', '')

        # Adjust 'cobc' executable name for Windows
        cobc_executable = "cobc"
        if sys.platform.startswith('win'):
            cobc_executable += ".exe"

        compile_command = [os.path.join(gnubase, "bin", cobc_executable), "-x", "-o", exe_path, self.current_file]

        try:
            process = subprocess.run(
                compile_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            if process.returncode == 0:
                self.status_bar.showMessage("Compilation successful!", 5000)
                QMessageBox.information(self, "Success", "Compilation successful!")
            else:
                self.status_bar.showMessage("Compilation failed", 5000)
                QMessageBox.critical(self, "Error", f"Compilation failed:\n{process.stderr}")
        except FileNotFoundError:
            QMessageBox.critical(
                self,
                "GnuCOBOL Not Found",
                "Could not find the 'cobc' compiler.\n"
                "Make sure GnuCOBOL is installed and in your system PATH, or specify its full path."
            )
        except Exception as e:
            self.status_bar.showMessage("Error during compilation", 5000)
            QMessageBox.critical(self, "Error", f"Could not compile file:\n{str(e)}")

    # --------------------------------------------------------------------
    #  EVENT OVERRIDES
    # --------------------------------------------------------------------
    def closeEvent(self, event) -> None:
        """
        Reimplement the closeEvent to prompt for unsaved changes before exiting.
        """
        if self._document_is_modified():
            result = self._prompt_save_discard_cancel("Do you want to save your changes before exiting?")
            if result is None:  # 'Cancel'
                event.ignore()
                return
        event.accept()

    # --------------------------------------------------------------------
    #  HELPER METHODS
    # --------------------------------------------------------------------
    def _open_file(self, file_path: str) -> None:
        """
        Open and read the file at 'file_path', then set it as current_file.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.editor.setPlainText(content)
            self.current_file = file_path
            self._update_window_title()
            self.status_bar.showMessage(f"File opened: {file_path}", 5000)
            self.editor.document().setModified(False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open file:\n{str(e)}")

    def _save_to_path(self, file_path: str) -> None:
        """
        Write the current editor contents to 'file_path', then update current_file.
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self.current_file = file_path
            self._update_window_title()
            self.editor.document().setModified(False)
            self.status_bar.showMessage(f"File saved: {file_path}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file:\n{str(e)}")

    def _document_is_modified(self) -> bool:
        """
        Return True if the current document has unsaved changes, else False.
        """
        return self.editor.document().isModified()

    def _update_window_title(self) -> None:
        """
        Update the window's title based on the currently open file (if any).
        """
        base_title = "GNU Cobol IDE"
        if self.current_file:
            filename = os.path.basename(self.current_file)
            self.setWindowTitle(f"{base_title} - {filename}")
        else:
            self.setWindowTitle(f"{base_title} - Untitled")

    def _prompt_save_discard_cancel(self, message: str) -> Optional[bool]:
        """
        Show a message box asking the user whether to Save, Discard, or Cancel.
        Returns:
            True if the user saved,
            False if the user discarded,
            None if the user canceled.
        """
        reply = QMessageBox.warning(
            self,
            "Unsaved Changes",
            message,
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save
        )
        if reply == QMessageBox.StandardButton.Save:
            self.handle_save_file()
            return True
        elif reply == QMessageBox.StandardButton.Discard:
            return False
        return None  # Cancel


# ------------------------------------------------------------------------
#  MAIN ENTRY POINT
# ------------------------------------------------------------------------
def main() -> None:
    app = QApplication(sys.argv)
    ide = CobolIDE()
    ide.show()
    sys.exit(app.exec())  # Updated from exec_() to exec()


if __name__ == "__main__":
    main()
