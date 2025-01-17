from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.db import connection
import pymysql
from sqlalchemy import create_engine, text as sql_text

from .search import search_species
from .models import EnsemblMetadata
from .utils import get_relevant_species

pymysql.install_as_MySQLdb()


# Create your views here.
def index(request):
    """
    View function for the index/search page of the
    taxonomy search django app.

    Parameters:
    request : GET request from the front-end containing the query string.

    Returns:
    render object (django.shortcuts.render): returns the response to the GET
    request with context/data required to display the results.

    """

    query_params = request.GET
    q = query_params.get("q")

    context = {}
    results = []
    if q is not None and len(q) > 1:
        # call the elastic search function in search.py
        search_results = search_species(q)

        name_class = [d["name_class"] for d in search_results][0]
        rank = [d["rank"] for d in search_results][0]

        matched_species = set([d["species_taxon_id"] for d in search_results])
        species_names = EnsemblMetadata.objects.filter(taxonomy_id__in=matched_species)

        context["query"] = q
        context["match_type"] = "exact"

        ### Determine if result/match type as per below conditions.
        # if name_class = scientific_name & rank = species is exact match
        # if name_class != scientific_name & rank = species is returning synonyms
        #   then [returning synonym species for]
        # if name_class = scientific_name & rank != species is species under provided rank
        #   then [returning closely related species under given rank]
        # if name_class != scientific_name & rank != species is rank synonyms + species under provided rank
        # if no species found then traverse the tree and return species under common ancestors
        #   then [returning species under common ancestor]

        if len(species_names) > 0:
            if name_class != "scientific name" and rank == "species":
                context["match_type"] = "synonym"
            elif rank != "species":
                context["match_type"] = "related"
                context["rank"] = rank

            species_list = [species_names[i].__dict__ for i in range(0, len(species_names))]
            for species in species_list:
                species["ensembl_url"] = "http://metazoa.ensembl.org/" + str(species["url_name"])
                results.append(species)
        else:
            for sp_dict in search_results:
                species_list, common_ancestor = get_relevant_species(sp_dict)
                for species in species_list:
                    species["ensembl_url"] = "http://metazoa.ensembl.org/" + str(species["url_name"])
                    results.append(species)

                context["match_type"] = "ancestor"
                context["common_ancestor"] = common_ancestor

    context["results"] = results

    return render(request, "index.html", context)


def taxon_tree(request, taxon_id):
    """
    View function (GET) for the taxon tree page of the
    taxonomy search django app.

    Parameters:
    request : GET request from the front-end containing the query string.
    taxon_id : taxon_id for which entire tree needs to be retrieved.


    Returns:
    render object (django.shortcuts.render): returns the response to the GET
    request with context/data required to display the results.

    """

    query = f"""SELECT n2.taxon_id , n2.parent_id_id ,na.name
                    ,n2.rank ,na.name_class
                    ,n2.left_index, n2.right_index
                    FROM ncbi_taxa_node n1 
                    JOIN (ncbi_taxa_node n2
                        LEFT JOIN ncbi_taxa_name na 
                        ON n2.taxon_id = na.taxon_id_id AND na.name_class = "scientific name")  
                    ON n2.left_index <= n1.left_index 
                    AND n2.right_index >= n1.right_index 
                    WHERE n1.taxon_id = {taxon_id}
                    ORDER BY n2.left_index
            """

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    results = []
    for row in rows:
        entry = {}
        entry["taxon_id"] = row[0]
        entry["parent_id"] = row[1]
        entry["name"] = row[2]
        entry["rank"] = row[3]
        entry["name_class"] = row[4]
        results.append(entry)

    context = {}
    context["results"] = results
    context["query"] = taxon_id

    return render(request, "tree.html", context)
