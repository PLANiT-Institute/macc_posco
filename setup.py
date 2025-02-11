from setuptools import setup, find_packages
# Read requirements from requirements.txt
with open("requirements.txt") as f:
    requirements = f.read().splitlines()
setup(
    name="optimal_steel_pathway",
    version="0.1.0",
    packages=find_packages(),
    install_requires=requirements,  # Load dependencies from requirements.txt
    author="Jinsu Park, PLANiT Institute",
    author_email="jinsu@planit.institute",
    description="Cost optimization model for steel production pathways",
    url="https://github.com/PLANiT-Institute/macc_posco",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU V3 License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)