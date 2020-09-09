# Equations-dataset-generator
Explore wikipedia downloading equations pngs with their corresponding latex code.

## Installation
This program consists of a simple Python3 script and so, using it is very simple. First clone this repository in your directory of choice:

```bash
git clone https://github.com/JcJ99/Equations-dataset-generator.git
```

Then install the necessary dependencies:

```bash
pip install -r requirements.txt
```

## Usage
Execute this program using:

```bash
python generate_wikipedia_dataset.py
```

First the program will ask for the number of equations that the user desires to download. This program will explore Wikipedia pages downloading all equations as png as well as their Latex code. Since just asking for random pages and downloading equations is too slow, the program allows you to introduce one first Wikipedia page **NAME** (not link) which guides the program towards more mathematical topics. Once all the equations of this first page are downloaded, the program will continue looking for equations in others Wikipedia pages that are linked in the first one and so on.

This program can be stopped and resumed at any time and uses a database to remember the already explored pages as well as the topics liked to those ones which remain to be explored.

The number of equations first introduced is only orientative. The program will stop once that number is **surpassed**, so usually some more equations will be downloaded.