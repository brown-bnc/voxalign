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
    QApplication, QWidget, QPushButton, QTextEdit, QVBoxLayout, QFileDialog, QMessageBox, QHBoxLayout, QLabel, QGroupBox, QFrame
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt


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
        self.setGeometry(100, 100, 800, 800)
        layout = QVBoxLayout()

        # Create a section for the session 1 inputs
        session1_label = QLabel("Session 1")
        session1_label.setAlignment(Qt.AlignHCenter)
        session1_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        session1_group = QGroupBox("")
        session1_layout = QVBoxLayout()
        session1_layout.addWidget(session1_label)

        self.session1_T1_label = QTextEdit("No session 1 T1 selected",self)
        self.session1_T1_label.setReadOnly(True)
        session1_layout.addWidget(self.session1_T1_label)

        # Session 1 T1 DICOM selection
        row = QHBoxLayout()
        row.addStretch(1)

        self.session1_T1_button = QPushButton("Select Session 1 T1 DICOM", self)
        self.session1_T1_button.clicked.connect(self.select_session1_T1_dicom)
        row.addWidget(self.session1_T1_button)
        self.session1_T1_clear  = QPushButton("Clear", self)
        self.session1_T1_clear.clicked.connect(self.clear_session1_T1)
        row.addWidget(self.session1_T1_clear)
        row.addStretch(1)
        session1_layout.addLayout(row)

        session1_layout.addWidget(QLabel(""))  # Add a blank line

        # Session 1 Spectroscopy DICOMs selection        
        self.session1_spec_label = QTextEdit("No spectroscopy DICOM(s) selected",self)
        self.session1_spec_label.setReadOnly(True)
        session1_layout.addWidget(self.session1_spec_label)
        row = QHBoxLayout()
        row.addStretch(1)

        self.session1_spec_button = QPushButton("Add Session 1 Spectroscopy DICOM(s)", self)
        self.session1_spec_button.clicked.connect(self.select_session1_spectroscopy_dicoms)
        row.addWidget(self.session1_spec_button)
        self.session1_spec_clear  = QPushButton("Clear", self)
        self.session1_spec_clear.clicked.connect(self.clear_session1_spec)
        row.addWidget(self.session1_spec_clear)
        row.addStretch(1)
        session1_layout.addLayout(row)
        session1_group.setLayout(session1_layout)
        layout.addWidget(session1_group)

        # Add a horizontal line divider between session 1 and session 2 inputs
        layout.addWidget(QLabel(""))  # Add a blank line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        layout.addWidget(QLabel(""))  # Add a blank line

        # Create a section for the session 2 inputs
        session2_label = QLabel("Session 2")
        session2_label.setAlignment(Qt.AlignHCenter)  # Center the text
        session2_label.setStyleSheet("font-weight: bold; font-size: 14pt;")

        session2_group = QGroupBox("")
        session2_layout = QVBoxLayout()
        session2_layout.addWidget(session2_label)

        # Session 2 T1 DICOM selection        
        self.session2_T1_label = QTextEdit("No session 2 T1 selected", self)
        self.session2_T1_label.setReadOnly(True)
        session2_layout.addWidget(self.session2_T1_label)
        row = QHBoxLayout()
        row.addStretch(1)

        self.session2_T1_button = QPushButton("Select Session 2 T1 DICOM", self)
        self.session2_T1_button.clicked.connect(self.select_session2_T1_dicom)
        row.addWidget(self.session2_T1_button)
        self.session2_T1_clear  = QPushButton("Clear", self)
        self.session2_T1_clear.clicked.connect(self.clear_session2_T1)
        row.addWidget(self.session2_T1_clear)
        row.addStretch(1)
        session2_layout.addLayout(row)
        session2_group.setLayout(session2_layout)
        layout.addWidget(session2_group)

        # Add a horizontal line divider between session 1 and session 2 inputs
        layout.addWidget(QLabel(""))  # Add a blank line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        layout.addWidget(QLabel(""))  # Add a blank line

        # Output folder selection        
        self.output_label = QTextEdit("No output folder selected",self)
        self.output_label.setReadOnly(True)
        layout.addWidget(self.output_label)
        row = QHBoxLayout()
        row.addStretch(1)
        self.output_button = QPushButton("Select Output Folder", self)
        self.output_button.clicked.connect(self.select_output_folder)
        row.addWidget(self.output_button)
        row.addStretch(1)
        layout.addLayout(row)


        # Run VoxAlign button
        layout.addWidget(QLabel(""))  # Adds a blank line visually
        row = QHBoxLayout()
        row.addStretch(1)

        self.run_button = QPushButton("Run VoxAlign", self)
        self.run_button.clicked.connect(self.run_voxalign)
        row.addWidget(self.run_button)
        row.addStretch(1)
        layout.addLayout(row)

        self.setLayout(layout)
        self.run_button.setEnabled(False)

    def select_output_folder(self):
        global output_folder
        output_folder = Path(QFileDialog.getExistingDirectory(self, "Select Output Folder"))
        if output_folder:
            if " " in str(output_folder):
                output_folder=""
                self.output_label.setText("Folders and filenames may not contain spaces. Please try again.")            
            else:
                self.output_label.setText(str(output_folder))
        else:
            self.output_label.setText("No output folder selected")
        self.validate_fields()

    def select_session1_T1_dicom(self):
        global session1_T1_dicom
        session1_T1_dicom, _ = QFileDialog.getOpenFileName(self, "Select Session 1 T1 DICOM", "", "DICOM files (*.dcm)")
        if session1_T1_dicom:
            if " " in str(session1_T1_dicom):
                session1_T1_dicom=""
                self.session1_T1_label.setText("Folders and filenames may not contain spaces. Please try again.")            
            else:
                self.session1_T1_label.setHtml(self.display_T1_info(session1_T1_dicom))
        else:
            self.session1_T1_label.setText("No session 1 T1 selected")
        self.validate_fields()

    def select_session2_T1_dicom(self):
        global session2_T1_dicom
        session2_T1_dicom, _ = QFileDialog.getOpenFileName(self, "Select Session 2 T1 DICOM", "", "DICOM files (*.dcm)")
        if session2_T1_dicom:
            if " " in str(session2_T1_dicom):
                session2_T1_dicom=""
                self.session2_T1_label.setText("Folders and filenames may not contain spaces. Please try again.")            
            else:
                self.session2_T1_label.setHtml(self.display_T1_info(session2_T1_dicom))
        else:
            self.session2_T1_label.setText("No session 2 T1 selected")
        self.validate_fields()

    def select_session1_spectroscopy_dicoms(self):
        global selected_spectroscopy_files
        files, _ = QFileDialog.getOpenFileNames(self, "Select Session 1 Spectroscopy DICOMs", "", "DICOM files (*.dcm)")
        
        if files:
            display_lines = []

            selected_spectroscopy_files.extend(files)
            selected_spectroscopy_files = sorted(list(set(selected_spectroscopy_files)))  # Remove duplicates

            if any(" " in file for file in selected_spectroscopy_files):
                selected_spectroscopy_files = []
                self.session1_spec_label.setText("Folders and filenames may not contain spaces. Please try again.")
                return

            for specdcm in selected_spectroscopy_files[:]:  # iterate over a copy for safe removal
                try:
                    spec_dcm_header = pydicom.dcmread(specdcm, stop_before_pixels=True)
                    description = getattr(spec_dcm_header, "SeriesDescription", "No Description")
                    patientname = getattr(spec_dcm_header, "PatientName", "No participant name")
                    image_type = getattr(spec_dcm_header, "ImageType", [])
                    filename = Path(specdcm).name

                    if not ("ORIGINAL" in image_type and "SPECTROSCOPY" in image_type):
                        response = QMessageBox.warning(
                            self, "Not spectroscopy DICOM",
                            f"This DICOM does not appear to be spectroscopy:\n\n{description} ({filename})\n\nDo you want to keep it?",
                            QMessageBox.Yes | QMessageBox.No
                        )

                        if response == QMessageBox.No:
                            selected_spectroscopy_files.remove(specdcm)
                            continue  # skip adding to display_lines

                    # Add to display list
                    display_lines.append(f"""
                        <span>{patientname}: <b>{description}</b></span>
                        <span style='color: gray; font-size: 10pt;'>{filename}</span><br>
                        """)

                except Exception as e:
                    print(f"Error reading DICOM {specdcm}: {e}")
                    continue

            if selected_spectroscopy_files:
                self.session1_spec_label.setText("\n".join(display_lines))
            else:
                self.session1_spec_label.setText("No valid spectroscopy files selected.")
        else:
            self.session1_spec_label.setText("No spectroscopy DICOM(s) selected")
        self.validate_fields()

    def clear_session1_T1(self):
        global session1_T1_dicom
        session1_T1_dicom = ""
        self.session1_T1_label.setText("No session 1 T1 selected")
        self.validate_fields()

    def clear_session2_T1(self):
        global session2_T1_dicom
        session2_T1_dicom = ""
        self.session2_T1_label.setText("No session 2 T1 selected")
        self.validate_fields()

    def clear_session1_spec(self):
        global selected_spectroscopy_files
        selected_spectroscopy_files = []
        self.session1_spec_label.setText("No session 1 T1 selected")
        self.validate_fields()

    def display_T1_info(self,T1dcm):
        display_text = ""
        try:
            dcm_header = pydicom.dcmread(T1dcm, stop_before_pixels=True)
            description = getattr(dcm_header, "SeriesDescription", "No description")
            patientname = getattr(dcm_header, "PatientName", "No participant name")
            display_text = f"""
            <span>{patientname}: <b>{description}</b></span><br><br>
            <span style='color: gray; font-size: 10pt;'>{T1dcm}</span>
            """
            return display_text
        except Exception as e:
            print(f"Error reading DICOM {T1dcm}: {e}")
        
    def validate_fields(self):
        all_fields_filled = all([
            bool(output_folder),
            bool(session1_T1_dicom),
            bool(session2_T1_dicom),
            bool(selected_spectroscopy_files)
        ])

        # Create a QFont object
        font = QFont()
        # Set the font weight to bold if all fields are filled
        font.setBold(all_fields_filled)
        self.run_button.setFont(font)
        self.run_button.setEnabled(all_fields_filled)


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
            command = f"dcm2niix -f sess1_T1 -o '{output_folder}' -s y -z n {session1_T1_dicom}"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            #skull strip session 1 T1
            print("\n...\nSkull stripping session 1 T1 ...")
            command = f"bet2 sess1_T1.nii sess1_T1_ss.nii"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            # Convert session 2 T1 DICOM to NIFTI
            command = f"dcm2niix -f sess2_T1 -o '{output_folder}' -s y -z n {session2_T1_dicom}"
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