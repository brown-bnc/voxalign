from setuptools import setup, find_packages

setup(
    name="voxalign",                
    version="0.1",                   
    packages=find_packages(),         
    install_requires=[                # List of dependencies
        "numpy",
        "pydicom",
        "nibabel",
        "spec2nii",
        "dcm2niix"                         
        # Add any other dependencies here
    ],
    entry_points={
        'console_scripts': [
            'run-voxalign=voxalign.main:run_voxalign',   # Entry point for running the script
        ]
    },
    include_package_data=True,        # Include any additional data files
    description="A tool to automate MRS voxel prescription to match existing data",  # A short description of your package
    author="Elizabeth Lorenc",               # Your name as the package author
    url="https://github.com/brownbnc/voxalign",  # URL to your project, if available
    classifiers=[                     # Classifiers for your package
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
)
