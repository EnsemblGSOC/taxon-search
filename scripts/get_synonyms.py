import re

from bs4 import BeautifulSoup
import pandas as pd
import pymysql
import requests
from sqlalchemy import create_engine


pymysql.install_as_MySQLdb()


def get_taxon_ids(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "lxml")

    table = soup.find("table")  # {"class": "data_table exportable ss autocenter"}
    taxon_dfs = pd.read_html(str(table))
    taxon_ids = taxon_dfs[0]["Taxon ID"].unique()
    print("extracted taxonomy ids:", len(taxon_ids))

    return taxon_ids


def preprocess_name(text):
    name = text["name"]
    if text["name_class"] != "scientific name":
        name = re.sub(r"[,.;@#?!&$\(\)]+\ *", " ", name)
        name = re.sub(" +", " ", name)

    out = name.lower().replace(" ", "_").strip("_")
    return out


def get_taxon_names(taxon_ids, db_conn):
    query_df = pd.DataFrame()
    for i in range(len(taxon_ids[:])):
        taxon_id = taxon_ids[i]
        query = f"""SELECT n2.* , na.name, na.name_class
                    FROM ncbi_taxa_node n1 
                    JOIN (ncbi_taxa_node n2
                        LEFT JOIN ncbi_taxa_name na 
                        ON n2.taxon_id = na.taxon_id)  
                    ON n2.left_index <= n1.left_index 
                    AND n2.right_index >= n1.right_index 
                    WHERE n1.taxon_id = {taxon_id}
                    ORDER BY left_index"""
        df = pd.read_sql_query(query, db_conn)
        df["query_taxon_id"] = taxon_id

        query_df = pd.concat([query_df, df])

    query_df = query_df.drop_duplicates()

    syn_df = query_df[
        (query_df["name_class"].isin(["scientific name", "synonym", "equivalent name"]))
        & (~query_df["rank"].isin(["no rank"]))
    ].reset_index(drop=1)

    syn_df["name"] = syn_df.apply(lambda r: preprocess_name(r), axis=1)

    syn_df = (
        syn_df.sort_values(by=["query_taxon_id", "rank"], ascending=False)
        .groupby(["query_taxon_id"])["name"]
        .apply(", ".join)
        .reset_index()
    )

    return syn_df


if __name__ == "__main__":
    species_url = "https://metazoa.ensembl.org/species.html"
    ncbi_engine = create_engine("mysql://anonymous@ensembldb.ensembl.org:3306/ncbi_taxonomy_109")
    db_conn = ncbi_engine.connect()

    metazoa_ids = get_taxon_ids(species_url)
    taxon_syns = get_taxon_names(metazoa_ids, db_conn)

    # count the synonyms
    taxon_syns["len"] = taxon_syns["name"].str.split(",").str.len()

    # filter on taxons having at least 1 synonym
    elastic_syn = taxon_syns[taxon_syns["len"] > 1]

    # save the synonyms into a text file to load into elastic search
    elastic_syn["name"].to_csv("taxon-elastic-search.syn", header=None, index=None, sep=",")
