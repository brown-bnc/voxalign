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

import numpy as np
import nibabel as nib
import glob
import subprocess
import os
import pydicom
np.set_printoptions(suppress=True)
from pathlib import Path
import sys
from voxalign.utils import check_external_tools, calc_prescription_from_nifti, convert_signs_to_letters, get_unique_filename, vox_to_scaled_FSL_vox
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QTextEdit, QVBoxLayout, QFileDialog, QMessageBox
)

# Global variables to store selected paths
output_folder = ""
session1_T1_dicom = ""
session2_T1_dicom = ""
selected_spectroscopy_files = []

class VoxAlignApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("VoxAlign DICOM Selector")
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
        self.session1_T1_button = QPushButton("Select Session 1 T1 DICOM", self)
        self.session1_T1_button.clicked.connect(self.select_session1_T1_dicom)
        layout.addWidget(self.session1_T1_button)

        self.session1_T1_label = QTextEdit(self)
        self.session1_T1_label.setReadOnly(True)
        layout.addWidget(self.session1_T1_label)

        # Session 2 T1 DICOM selection
        self.session2_T1_button = QPushButton("Select Session 2 T1 DICOM", self)
        self.session2_T1_button.clicked.connect(self.select_session2_T1_dicom)
        layout.addWidget(self.session2_T1_button)

        self.session2_T1_label = QTextEdit(self)
        self.session2_T1_label.setReadOnly(True)
        layout.addWidget(self.session2_T1_label)

        # Session 1 Spectroscopy DICOMs selection
        self.session1_spec_button = QPushButton("Add Session 1 Spectroscopy DICOMs", self)
        self.session1_spec_button.clicked.connect(self.select_session1_spectroscopy_dicoms)
        layout.addWidget(self.session1_spec_button)

        self.session1_spec_label = QTextEdit(self)
        self.session1_spec_label.setReadOnly(True)
        layout.addWidget(self.session1_spec_label)

        # Run VoxAlign button
        self.run_button = QPushButton("Run VoxAlign", self)
        self.run_button.clicked.connect(self.run_voxalign)
        layout.addWidget(self.run_button)

        self.setLayout(layout)

    def select_output_folder(self):
        global output_folder
        output_folder = Path(QFileDialog.getExistingDirectory(self, "Select Output Folder"))
        if output_folder:
            self.output_label.setText(str(output_folder))
        else:
            self.output_label.setText("No folder selected")

    def select_session1_T1_dicom(self):
        global session1_T1_dicom
        session1_T1_dicom, _ = QFileDialog.getOpenFileName(self, "Select Session 1 T1 DICOM", "", "DICOM files (*.dcm)")
        if session1_T1_dicom:
            self.session1_T1_label.setText(session1_T1_dicom)
        else:
            self.session1_T1_label.setText("No file selected")

    def select_session2_T1_dicom(self):
        global session2_T1_dicom
        session2_T1_dicom, _ = QFileDialog.getOpenFileName(self, "Select Session 2 T1 DICOM", "", "DICOM files (*.dcm)")
        if session2_T1_dicom:
            self.session2_T1_label.setText(session2_T1_dicom)
        else:
            self.session2_T1_label.setText("No file selected")

    def select_session1_spectroscopy_dicoms(self):
        global selected_spectroscopy_files
        files, _ = QFileDialog.getOpenFileNames(self, "Select Session 1 Spectroscopy DICOMs", "", "DICOM files (*.dcm)")
        if files:
            selected_spectroscopy_files.extend(files)
            selected_spectroscopy_files = sorted(list(set(selected_spectroscopy_files)))  # Remove duplicates
            self.session1_spec_label.setText(", ".join(selected_spectroscopy_files))
        else:
            self.session1_spec_label.setText("No files selected")

    def run_voxalign(self):
        self.run_button.setDisabled(True)
        try:
            check_external_tools()

            print("Running VoxAlign!")
            print("\nOutput folder:", output_folder)
            print("\nSession 1 T1 DICOM:", session1_T1_dicom)
            print("\nSession 2 T1 DICOM:", session2_T1_dicom)
            print("\nSession 1 Spectroscopy DICOMs:", selected_spectroscopy_files)

            os.chdir(output_folder)

            #read T1 DICOM headers to get info about study, date, participant, etc.
            # sess1T1_dicom_header = pydicom.dcmread(session1_T1_dicom,stop_before_pixels=True)
            sess2T1_dicom_header = pydicom.dcmread(session2_T1_dicom,stop_before_pixels=True)

            #convert session 1 T1 DICOM to NIFTI
            command = f"dcm2niix -f sess1_T1 -o '{output_folder}' -s y {session1_T1_dicom}"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            #skull strip session 1 T1
            print("\n...\nSkull stripping session 1 T1 ...")
            command = f"bet2 sess1_T1.nii sess1_T1_ss.nii"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            # Convert session 2 T1 DICOM to NIFTI
            command = f"dcm2niix -f sess2_T1 -o '{output_folder}' -s y {session2_T1_dicom}"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            #skull strip session 2 T1
            print("Skull stripping session 2 T1 ...")
            command = f"bet2 sess2_T1.nii sess2_T1_ss.nii"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            # use flirt to register session 1 T1 to session 2 T1
            print("Aligning session 1 T1 to session 2 T1 ...")
            command = f"flirt -in sess1_T1_ss.nii.gz -ref sess2_T1_ss.nii.gz -out sess1_T1_aligned -omat sess1tosess2.mat -dof 6"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            # Convert session 1 spectroscopy DICOM(s)  to NIFTI & transform
            for dcm in selected_spectroscopy_files:

                #File names can be specified with the -f option and output directories with the -o option.
                command = f"spec2nii 'dicom' -o '{output_folder}/sess1_svs/tmp' {dcm}"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                #print(result)

                #start by placing spec niftis in a temp folder so we can make sure not to overwrite
                tmp_nifti = glob.glob(f'{output_folder}/sess1_svs/tmp/*')[0]
                suffix = ''.join(Path(tmp_nifti).suffixes)
                roi=Path(tmp_nifti.removesuffix(suffix)).stem
                #if a file already exists, append _2, _3, etc.
                new_filename = get_unique_filename(f'sess1_svs/{roi}',suffix)
                roi=Path(new_filename.removesuffix(suffix)).stem

                command = f"mv {tmp_nifti} {new_filename}"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                command = "rm -r sess1_svs/tmp"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)

                spec_nii = nib.load(new_filename)
                sess1_nii = nib.load('sess1_T1.nii')
                sess2_nii = nib.load('sess2_T1.nii')

                if sess1_nii.header.get_zooms() != sess2_nii.header.get_zooms():
                    raise(Exception("Your session 1 and session 2 T1s must have the same voxel resolution"))

                sess1to2affine = np.loadtxt('sess1tosess2.mat')

                # combine affine transforms to go from sess 1 T1 -> sess 2 T1 via the flirt coregistration affine
                # flirt affine is in scaled voxel coordinates, with a sign flip in x if the determinant is positive                    
                sess1_voxtoFSL = vox_to_scaled_FSL_vox(sess1_nii)
                sess2_voxtoFSL = vox_to_scaled_FSL_vox(sess2_nii)

                transform =  sess2_nii.affine @ np.linalg.inv(sess2_voxtoFSL) @ sess1to2affine @ sess1_voxtoFSL @ np.linalg.inv(sess1_nii.affine)
                new_affine = transform @ spec_nii.affine

                aligned_spec = nib.load(new_filename) #start with session 1 spec nifti
                aligned_spec.set_sform(new_affine,code='unknown')#code='aligned')
                aligned_spec.set_qform(new_affine,code='scanner')
                nib.save(aligned_spec,f'{roi}_aligned.nii.gz')

                slice_orientation_pitch,inplane_rot,[dimX,dimY,dimZ] = calc_prescription_from_nifti(spec_nii)
                transvec = convert_signs_to_letters(np.round(spec_nii.affine[0:3,3],1))
                print("\n-------------")
                print(f"ROI: {roi}")
                print("-------------")
                print(f"PREVIOUS")
                print(f'Position: {transvec}')
                print(f"Orientation: {slice_orientation_pitch}")
                print(f"Rotation: {inplane_rot:.2f} deg")
                print(f"Dimensions: {dimX} mm x {dimY} mm x {dimZ} mm")

                slice_orientation_pitch,inplane_rot,[dimX,dimY,dimZ] = calc_prescription_from_nifti(aligned_spec)
                transvec = convert_signs_to_letters(np.round(aligned_spec.affine[0:3,3],1))

                # Define the file name based on the ROI
                filename = f"{roi}_prescription.txt"
                print(f"\nTODAY")
                print(f'Position: {transvec}')
                print(f"Orientation: {slice_orientation_pitch}")
                print(f"Rotation: {inplane_rot:.2f} deg")
                print(f"Dimensions: {dimX} mm x {dimY} mm x {dimZ} mm")

                try:
                    with open(filename, 'w') as file:
                        file.write(f"Study: {sess2T1_dicom_header.StudyDescription}")
                        file.write(f"\nDate: {sess2T1_dicom_header.StudyDate}")
                        file.write(f"\nParticipant: {sess2T1_dicom_header.PatientID}")
                        file.write(f'\nSession 1 T1 DICOM file: {Path(session1_T1_dicom).name}')
                        file.write(f'\nSession 2 T1 DICOM file: {Path(session2_T1_dicom).name}')
                        file.write(f'\nSession 1 Spectroscopy DICOM file: {Path(dcm).name}')
                        file.write(f"\n\n---------------------------\n\n")
                        file.write(f"NEW {roi} PRESCRIPTION\n")
                        file.write(f'Position: {transvec}\n')
                        file.write(f"Orientation: {slice_orientation_pitch}\n")
                        file.write(f"Rotation: {inplane_rot:.2f} deg\n")
                        file.write(f"Dimensions: {dimX} mm x {dimY} mm x {dimZ} mm")
                    print(f"Prescription written to {filename}")
                    print("-------------\n")
                except Exception as e:
                    print(f"Error writing to file: {e}")

            command = "fsleyes -ixh --displaySpace world sess1_T1.nii sess1_svs/*.nii.gz sess2_T1.nii *aligned.nii.gz"
            process = subprocess.Popen(command, shell=True)
            print("\nVoxAlign process completed successfully.\n")
            
            # Create and display the success message box
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.NoIcon)
            msg_box.setWindowTitle("Success")
            msg_box.setText("VoxAlign process completed successfully!")
            msg_box.setStandardButtons(QMessageBox.Ok)
            
            # If the user clicks "OK", close the application
            if msg_box.exec() == QMessageBox.Ok:
                self.close()  # Close the GUI window
                sys.exit()    # Exit the application

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            print(f"An error occurred: {e}")

        finally:
            self.run_button.setDisabled(False)

def start_voxalign():
    """Function to initialize and run the VoxAlign PyQt application."""
    app = QApplication(sys.argv)
    window = VoxAlignApp()
    window.show()
    sys.exit(app.exec_())