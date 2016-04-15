from distutils.core import setup
import sudoers_manager

setup(
    name='Sudoers Manager',
    version=sudoers_manager.attributes['version'],
    url='https://github.com/univ-of-utah-marriott-library-apple/sudoers_manager',
    author='Pierce Darragh, Marriott Library IT Services',
    author_email='mlib-its-mac-github@lists.utah.edu',
    description=('A standalone Python script to help administrators manage their sudoers file.'),
    license='MIT',
    scripts=['sudoers_manager.py'],
    classifiers=[
        'Development Status :: 5 - Stable',
        'Environment :: Console',
        'Environment :: MacOS X',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7'
    ],
)
