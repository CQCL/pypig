
from setuptools import setup, find_packages 
  
with open('requirements.txt') as f: 
    requirements = f.readlines() 

with open('README.md') as f:
    long_description = f.read()

  
setup( 
        name ='pypig', 
        version ='1.0.0', 
        author ='Seyon Sivarajah', 
        author_email ='seyon.sivarajah@cambridgequantum.com', 
        url ='https://github.com/CQCL/pypig', 
        description ="Command line tool for managing private pypiserver", 
        long_description = long_description, 
        long_description_content_type ="text/markdown", 
        license ='GPL', 
        packages = find_packages(), 
        entry_points ={ 
            'console_scripts': [ 
                'pypig = pypig.pypig:main'
            ] 
        }, 
        classifiers =( 
            "Programming Language :: Python :: 3", 
            "License :: OSI Approved :: GNU General Public License (GPL)", 
            "Operating System :: OS Independent", 
        ), 
        install_requires = requirements, 
        zip_safe = False
) 
