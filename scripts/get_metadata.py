import pymysql
pymysql.install_as_MySQLdb()

import requests
import pandas as pd
from sqlalchemy import create_engine, text as sql_text


def get_taxon_metadata(db_connection):
    
    query = f"""select distinct taxonomy_id ,o.name ,url_name 
                    ,display_name ,scientific_name ,strain
                    from organism o
                    left join genome g
                    on o.organism_id = g.organism_id 
                    left join division d 
                    on g.division_id = d.division_id
                    LEFT JOIN data_release USING (data_release_id)
                    where d.short_name = 'EM'
                    AND is_current = 1
                    """

    org_df = pd.read_sql_query(sql_text(query), db_connection)
    org_df = org_df.sort_values(by=['taxonomy_id'])
    org_df.to_csv("metazoa_metadata.csv", index=False)

    return org_df
    
if __name__ == "__main__":
    ncbi_engine = create_engine('mysql://anonymous@ensembldb.ensembl.org:3306/ensembl_metadata_109')
    db_conn = ncbi_engine.connect()

    metadata_df = get_taxon_metadata(db_conn)

    pk_col = []
    field_col = ['taxonomy_id', 'url_name', 'display_name', 'scientific_name', 'strain']
    m2_df = metadata_df[pk_col+field_col].drop_duplicates()
    
    m2_df['model'] = 'taxon_search.EnsemblMetadata' 
    # m2_df['pk'] = None
    m2_df['fields'] = m2_df[field_col].to_dict(orient="records")
    json_str = m2_df[['model', 'fields']].to_json(orient='records')
    with open("ensembl_metadata.json", "w") as outfile:
        outfile.write(json_str)

