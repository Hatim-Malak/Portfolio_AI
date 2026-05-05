def individual_serial(project) -> dict:
    return {
        "id":str(project["_id"]),
        "title":project["title"],
        "full_name":project["full_name"],
        "readme":project["readme"],
        "url":project["url"],
        "updated_at":project["updated_at"],
    }

def list_serial(projects) -> list:
    return [individual_serial(project) for project in projects]