from setuptools import setup, find_packages

setup(
    name="voxalign",                
    version="0.3",                   
    packages=find_packages(),         
    install_requires=[                # List of dependencies
        "numpy",
        "pydicom",
        "nibabel",
        "PyQt5",
        "spec2nii",
        "dcm2niix"
    ],
    entry_points={
        'console_scripts': [
            'run-voxalign=voxalign.main:start_voxalign',   # Entry point for running the script
            'dice-coef=voxalign.calc_dice_coef:start_dice',  # Separate tool to calculate dice coefficient after scan 2
            'mni-lookup=voxalign.mni_lookup:start_mnilookup',  # Separate tool to output voxel position based on center MNI coordinate
        ]
    },
    include_package_data=True,        # Include any additional data files
    description="A tool to automate MRS voxel prescription to match existing data or based on MNI coordinates",  # A short description of your package
    author="Elizabeth Lorenc",               # Your name as the package author
    url="https://github.com/brownbnc/voxalign",  # URL to your project, if available
    classifiers=[                     # Classifiers for your package
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
)
