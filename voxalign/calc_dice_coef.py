# Copyright 2025, Brown University, Providence, RI.
#
# All Rights Reserved
#
# Permission to use, copy, modify, and distribute this software and
# its documentation for any purpose other than its incorporation into a
# commercial product or service is hereby granted without fee, provided
# that the above copyright notice appear in all copies and that both
# that copyright notice and this permission notice appear in supporting
# documentation, and that the name of Brown University not be used in
# advertising or publicity pertaining to distribution of the software
# without specific, written prior permission.
#
# BROWN UNIVERSITY DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
# INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR ANY
# PARTICULAR PURPOSE. IN NO EVENT SHALL BROWN UNIVERSITY BE LIABLE FOR ANY
# SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import nibabel as nib
import numpy as np
import argparse
import os
import glob
from voxalign.utils import get_unique_filename
import subprocess
from pathlib import Path
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QTextEdit, QVBoxLayout, QFileDialog, QMessageBox
)
def convert_spec_dicom(dicomfile,outdir):
    command = f"spec2nii 'dicom' -o 'tmp' {dicomfile}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    #start by placing spec niftis in a temp folder so we can make sure not to overwrite
    tmp_nifti = glob.glob(f'{outdir}/tmp/*')[0]
    suffix = ''.join(Path(tmp_nifti).suffixes)
    roi=Path(tmp_nifti.removesuffix(suffix)).stem
    #if a file already exists, append _2, _3, etc.
    new_filename = get_unique_filename(f'{roi}',suffix)
    roi=Path(new_filename.removesuffix(suffix)).stem

    command = f"mv {tmp_nifti} {new_filename}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    command = "rm -r tmp"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    return new_filename

# Global variables to store selected paths
outdir = ""
sess1svs = ""
sess2svs = ""
sess1T1 = ""
sess2T1 = ""

class DiceApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("File Selector for Dice Coefficient Calculation")
        self.setGeometry(100, 100, 800, 400)
        layout = QVBoxLayout()

        # Output folder selection
        self.output_button = QPushButton("Select Output Folder", self)
        self.output_button.clicked.connect(self.select_output_folder)
        layout.addWidget(self.output_button)

        self.output_label = QTextEdit(self)
        self.output_label.setReadOnly(True)
        layout.addWidget(self.output_label)

        # Session 1 T1 DICOM selection
        self.session1_T1_button = QPushButton("Select Session 1 T1 DICOM/NIFTI", self)
        self.session1_T1_button.clicked.connect(self.select_session1_T1)
        layout.addWidget(self.session1_T1_button)

        self.session1_T1_label = QTextEdit(self)
        self.session1_T1_label.setReadOnly(True)
        layout.addWidget(self.session1_T1_label)

        # Session 2 T1 DICOM selection
        self.session2_T1_button = QPushButton("Select Session 2 T1 DICOM/NIFTI", self)
        self.session2_T1_button.clicked.connect(self.select_session2_T1)
        layout.addWidget(self.session2_T1_button)

        self.session2_T1_label = QTextEdit(self)
        self.session2_T1_label.setReadOnly(True)
        layout.addWidget(self.session2_T1_label)

        # Session 1 Spectroscopy DICOM or NIFTI selection
        self.session1_spec_button = QPushButton("Select Session 1 Spectroscopy DICOM/NIFTI", self)
        self.session1_spec_button.clicked.connect(self.select_session1_spectroscopy)
        layout.addWidget(self.session1_spec_button)

        self.session1_spec_label = QTextEdit(self)
        self.session1_spec_label.setReadOnly(True)
        layout.addWidget(self.session1_spec_label)

        # Session 2 Spectroscopy DICOM or NIFTI selection
        self.session2_spec_button = QPushButton("Select Session 2 Spectroscopy DICOM/NIFTI", self)
        self.session2_spec_button.clicked.connect(self.select_session2_spectroscopy)
        layout.addWidget(self.session2_spec_button)

        self.session2_spec_label = QTextEdit(self)
        self.session2_spec_label.setReadOnly(True)
        layout.addWidget(self.session2_spec_label)

        # Calculate Dice Coefficient button
        self.run_button = QPushButton("Calculate Dice Coefficient", self)
        self.run_button.clicked.connect(self.run_calc_dice_coef)
        layout.addWidget(self.run_button)

        self.setLayout(layout)

    def select_output_folder(self):
        global outdir
        outdir = Path(QFileDialog.getExistingDirectory(self, "Select Output Folder"))
        if outdir:
            self.output_label.setText(str(outdir))
        else:
            self.output_label.setText("No folder selected")

    def select_session1_T1(self):
        global sess1T1
        sess1T1, _ = QFileDialog.getOpenFileName(self, "Select Session 1 T1 ", "", "DICOM or NIFTI files (*.dcm *.nii *.nii.gz)")
        if sess1T1:
            self.session1_T1_label.setText(sess1T1)
        else:
            self.session1_T1_label.setText("No file selected")

    def select_session2_T1(self):
        global sess2T1
        sess2T1, _ = QFileDialog.getOpenFileName(self, "Select Session 2 T1", "", "DICOM or NIFTI files (*.dcm *.nii *.nii.gz)")
        if sess2T1:
            self.session2_T1_label.setText(sess2T1)
        else:
            self.session2_T1_label.setText("No file selected")

    def select_session1_spectroscopy(self):
        global sess1svs
        sess1svs, _ = QFileDialog.getOpenFileName(self, "Select Session 1 Spectroscopy File", "", "DICOM or NIFTI files (*.dcm *.nii *.nii.gz)")
        if sess1svs:
            self.session1_spec_label.setText(sess1svs)
        else:
            self.session1_spec_label.setText("No files selected")
    
    def select_session2_spectroscopy(self):
        global sess2svs
        sess2svs, _ = QFileDialog.getOpenFileName(self, "Select Session 2 Spectroscopy File", "", "DICOM or NIFTI files (*.dcm *.nii *.nii.gz)")
        if sess2svs:
            self.session2_spec_label.setText(sess2svs)
        else:
            self.session2_spec_label.setText("No files selected")

    def run_calc_dice_coef(self):
        """
        Calculates the Dice coefficient between svs voxels from different sessions.
        """
        self.run_button.setDisabled(True)

        try:
            if not os.path.exists(outdir):
                os.makedirs(outdir)
            os.chdir(outdir)

            # Convert any input svs DICOMs to NIFTI
            if Path(sess1svs).suffixes[-1] == ".dcm":
                sess1svs_nifti = convert_spec_dicom(sess1svs,outdir)
            else:
                sess1svs_nifti = sess1svs
            
            if Path(sess2svs).suffixes[-1] == ".dcm":
                sess2svs_nifti = convert_spec_dicom(sess2svs,outdir)
            else:
                sess2svs_nifti = sess2svs
            
            # Load svs and T1 niftis
            sess1svs_nii=nib.load(sess1svs_nifti)
            sess2svs_nii=nib.load(sess2svs_nifti)

            #session 1
            svsplaceholder=np.zeros((2,2,2))
            svsplaceholder[0, 0, 0] = 1.0
            tmp = nib.Nifti2Image(svsplaceholder, affine=sess1svs_nii.affine)
            nib.save(tmp,'sess1_svs_tmp.nii.gz')
            suffix = ''.join(Path(sess1svs_nifti).suffixes)
            sess1roi=f"sess1_{Path(sess1svs_nifti.removesuffix(suffix)).stem}"

            #prepare session 1 T1
            if not os.path.exists("sess1_T1.nii"):
                if Path(sess1T1).suffixes[-1] == ".nii":
                    result = subprocess.run(['cp', sess1T1, 'sess1_T1.nii'], capture_output=True, text=True)
                elif ''.join(Path(sess1T1).suffixes[-2:]) == ".nii.gz":
                    result = subprocess.run(['cp', sess1T1, 'sess1_T1.nii.gz'], capture_output=True, text=True)
                    result = subprocess.run(['gunzip', 'sess1_T1.nii.gz'], capture_output=True, text=True)
                elif Path(sess1T1).suffixes[-1] == ".dcm":
                    result = subprocess.run(['dcm2niix','-f','sess1_T1','-o', outdir,'-s','y',sess1T1], capture_output=True, text=True)
                    print(result)

            #skull strip session 1 T1
            if not os.path.exists("sess1_T1_ss.nii.gz"):
                print("\n...\nSkull stripping session 1 T1 ...")
                command = f"bet2 sess1_T1.nii sess1_T1_ss.nii.gz"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
            else:
                print("\n...\nFound existing skull stripped sess 1 T1 sess1_T1_ss.nii.gz")

            #prepare session 2 T1
            if not os.path.exists("sess2_T1.nii"):
                if Path(sess2T1).suffixes[-1] == ".nii":
                    result = subprocess.run(['cp', sess2T1, 'sess2_T1.nii'], capture_output=True, text=True)
                elif ''.join(Path(sess2T1).suffixes[-2:]) == ".nii.gz":
                    result = subprocess.run(['cp', sess2T1, 'sess2_T1.nii.gz'], capture_output=True, text=True)
                    result = subprocess.run(['gunzip', 'sess2_T1.nii.gz'], capture_output=True, text=True)
                elif Path(sess2T1).suffixes[-1] == ".dcm":
                    # command = f"dcm2niix -f sess2_T1 -s y {sess2T1}"
                    result = subprocess.run(['dcm2niix','-f','sess2_T1','-o', outdir,'-s','y',sess2T1], capture_output=True, text=True)

            #skull strip session 2 T1
            command = f"cp {sess2T1} ."
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if not os.path.exists("sess2_T1_ss.nii.gz"):
                print("\nSkull stripping session 2 T1 ...")
                command = f"bet2 sess2_T1.nii sess2_T1_ss.nii.gz"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
            else:
                print("\nFound existing skull stripped sess 2 T1 sess2_T1_ss.nii.gz")

            if not os.path.exists("sess1tosess2.mat"):
                # use flirt to register session 1 T1 to session 2 T1
                print("Aligning session 1 T1 to session 2 T1 ...")
                command = f"flirt -in sess1_T1_ss.nii -ref sess2_T1_ss.nii -out sess1_T1_aligned -omat sess1tosess2.mat -dof 6"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
            else:
                print("\nFound existing flirt affine transformation matrix sess1tosess2.mat")


            # command = f"flirt -in {sess1T1} -ref {sess1T1} -applyisoxfm .5 -nosearch -out sess1T1_hires.nii.gz"
            # result = subprocess.run(command, shell=True, capture_output=True, text=True)

            #resample sess1 svs to sess1 T1 with flirt
            command = f"flirt -in sess1_svs_tmp.nii.gz -ref sess1_T1.nii -out {sess1roi}_mask{suffix} -omat sess1spectosess1T1.mat -applyisoxfm .25 -noresampblur -usesqform -applyisoxfm .25 -setbackground 0 -paddingsize 1 -interp 'nearestneighbour'"

            # command = f"flirt -in sess1_svs_tmp.nii.gz -ref sess1T1_hires.nii.gz -out {sess1roi}_mask{suffix} -omat sess1spectosess1T1.mat -usesqform -applyxfm"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            print(result)

            command='convert_xfm -omat spec1tosess2T1.mat -concat sess1tosess2.mat sess1spectosess1T1.mat '
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            print(result)

            #session 2
            tmp = nib.Nifti2Image(svsplaceholder, affine=sess2svs_nii.affine)
            suffix = ''.join(Path(sess2svs_nifti).suffixes)
            sess2roi=f"sess2_{Path(sess2svs_nifti.removesuffix(suffix)).stem}"
            nib.save(tmp,'sess2_svs_tmp.nii.gz')

            command=f"flirt -in sess2_svs_tmp.nii.gz -ref sess2_T1.nii -out {sess2roi}_tosess2T1{suffix} -usesqform -applyisoxfm .25 -setbackground 0 -paddingsize 1 -interp 'nearestneighbour' " #
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            print(result)

            # now transform sess1 svs
            command=f"flirt -in sess1_svs_tmp.nii.gz -ref sess2_T1.nii -out {sess1roi}_tosess2T1{suffix} -usesqform -applyisoxfm .25 -init spec1tosess2T1.mat -setbackground 0 -paddingsize 1 -interp 'nearestneighbour'" # 
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            print(result)

            vox1nii = nib.load(f"{sess1roi}_tosess2T1{suffix}")
            vox1 = vox1nii.get_fdata()

            vox2nii = nib.load(f"{sess2roi}_tosess2T1{suffix}")
            vox2 = vox2nii.get_fdata()

            intersection = np.logical_and(vox1, vox2).sum()
            dice = 2 * intersection / (vox1.sum() + vox2.sum())
            print(f"Dice coefficient: {dice:.2f}")
            return dice
    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            print(f"An error occurred: {e}")

        finally:
            self.run_button.setDisabled(False)

def start_dice():
    """Function to initialize and run the Dice Coefficient PyQt application."""
    app = QApplication(sys.argv)
    window = DiceApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    start_dice()
