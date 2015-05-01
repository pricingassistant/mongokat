from setuptools import setup  # , find_packages
import os


def get_requirements():
    reqs = []
    for filename in ["requirements.txt"]:
        with open(filename, "r") as f:
            reqs += [x.strip() for x in f.readlines() if x.strip() and not x.strip().startswith("#")]
    return reqs


def get_version():
    basedir = os.path.dirname(__file__)
    with open(os.path.join(basedir, 'mongokat/version.py')) as f:
        locals = {}
        exec(f.read(), locals)
        return locals['VERSION']
    raise RuntimeError('No version info found.')

setup(
    name="mongokat",
    include_package_data=True,
    packages=['mongokat'],
    version=get_version(),
    description="Lightweight MongoDB ORM/ODM",
    author="Pricing Assistant",
    license='MIT',
    author_email="contact@pricingassistant.com",
    url="http://github.com/pricingassistant/mongokat",
    # download_url="http://chardet.feedparser.org/download/python3-chardet-1.0.1.tgz",
    keywords=["mongodb", "mongo", "orm", "odm", "mongokit"],
    platforms='any',
    entry_points={
        'console_scripts': [
        ]
    },
    # dependency_links=[
    #     "http://github.com/mongodb/mongo-python-driver/archive/cb4adb2193a83413bc5545d89b7bbde4d6087761.zip#egg=pymongo-2.7rc1"
    # ],
    zip_safe=False,
    install_requires=get_requirements(),
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        #'Development Status :: 1 - Planning',
        #'Development Status :: 2 - Pre-Alpha',
        #'Development Status :: 3 - Alpha',
        'Development Status :: 4 - Beta',
        #'Development Status :: 5 - Production/Stable',
        #'Development Status :: 6 - Mature',
        #'Development Status :: 7 - Inactive',
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Utilities"
    ],
    long_description=open("docs/index.rst").read()
)
