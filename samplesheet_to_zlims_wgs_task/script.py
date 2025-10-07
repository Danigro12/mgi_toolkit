import csv
from pathlib import Path
import sys
import json
import pandas as pd
import configparser
import shutil


# --- Args ---

config = configparser.ConfigParser()
config.read("config.ini")

barcode_csv_path, ztron_path, reference, lib_type, standard_sample = (Path(config["paths"]["barcode_csv_path"]),
                                                                      Path(config["paths"]["ztron_path"]),
                                                                      Path(config["paths"]["reference"]),
                                                                      Path(config["paths"]["lib_type"]),
                                                                      Path(config["paths"]["standard_sample"])
                                                                      )

print("\n")
print(f"Input file: {barcode_csv_path}")

base_dir = Path(__file__).parent 

""" parent_dir = Path(barcode_csv_path).parent
print(f"Output dir: {parent_dir}") """

# --- vars ---
barcode_dict = {}
rows = []
dataframe = pd.read_csv(barcode_csv_path, dtype=str, header=None, names=["Sample", "Sequence"])

# --- Get Flowcell ID ---
flowcell = dataframe["Sequence"][0]

# --- Removing DataFrame's head ---
dataframe = dataframe.iloc[3:,].reset_index(drop=True)

# --- Input summary ---
print("\n=== Input Summary ===")
print("\n")
print(f"Flowcell ID: {flowcell}")
print("\n")
print(dataframe.to_string(index=False))
print("\n")
print("Searching for run ID...")
print("\n")

json_path = base_dir.parent.parent / "barcodes" / "barcodes_mgi.json"

with open(json_path, "r") as f:
    barcodes = json.load(f)

dataframe["Barcode"] = dataframe["Sequence"].map({v: k for k, v in barcodes.items()})

# --- Get job ID ---

matches = list(ztron_path.rglob(f"{flowcell}_L01.summaryReport.html"))

if not matches:
    raise FileNotFoundError(f"No {flowcell} file in {base_dir}")

if len(matches) == 1:
    selected_path = matches[0].parent
else:
    print("More than one job found.")
    for i, p in enumerate(matches):
        print(f"{i+1}: {p.parent}")
    choice = int(input("Select the number of the correct option:"))
    selected_path = matches[choice - 1].parent

#selected_path = "/mnt/z/ztron/autorunDW/DNBSEQ-T7/R2100610220009/write_fastq_config_1_5/ztron/E250077027_L01_14525/E250077027_L01"

dataframe_final = pd.read_excel("blank.xls", dtype=str)

# -- 

dataframe["sampleId"] = flowcell + "_" + dataframe["Barcode"] + "_" + dataframe["Sample"]
dataframe["sampleName"] = dataframe["Sample"]
dataframe["Reference"] = reference
dataframe["WGS-mode"] = lib_type
dataframe["standard sample"] = standard_sample
dataframe["files.read1"] = dataframe["sampleName"].apply(
    lambda x: str(selected_path / f"{flowcell}_L01_{x}_1.fq.gz")
)
dataframe["files.read2"] = dataframe["sampleName"].apply(
    lambda x: str(selected_path / f"{flowcell}_L01_{x}_2.fq.gz")
)

def ajustar_caminho(path_str):
    # Garante que é string
    path_str = str(path_str)
    # Se já começa com /storeData, retorna como está
    if path_str.startswith("/storeData"):
        return path_str
    # Procura por /ztron/autorunDW e insere /storeData antes
    idx = path_str.find("/ztron/autorunDW")
    if idx != -1:
        return "/storeData" + path_str[idx:]
    # Se não encontrar, retorna original
    return path_str

dataframe["files.read1"] = dataframe["files.read1"].apply(ajustar_caminho)
dataframe["files.read2"] = dataframe["files.read2"].apply(ajustar_caminho)

dataframe_final = pd.concat([dataframe_final, dataframe[["sampleId", "sampleName", "Reference", "WGS-mode", "standard sample", "files.read1", "files.read2"]]])

with pd.ExcelWriter(f"results/{flowcell}_zlims_wgs_samplesheet.xlsx", engine='openpyxl') as writer:
        dataframe_final.to_excel(writer, sheet_name='Sheet1', index=False)

print(f"Done! Samplesheet created for flowcell: {flowcell}")
print("\n")
