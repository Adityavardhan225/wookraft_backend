class Rules:

    # single database operations

    @staticmethod
    def add(data, cluster, database, collection):
        return cluster[database][collection].insert_one(data).inserted_id

    @staticmethod
    def get(query, cluster, database, collection):
        return cluster[database][collection].find_one(query)

    @staticmethod
    def update(query, data, cluster, database, collection):
        return cluster[database][collection].update_one(query, data)

    @staticmethod
    def delete(query, cluster, database, collection):
        return cluster[database][collection].delete_one(query)

    # multiple database operations

    @staticmethod
    def add_many(data, cluster, database, collection):
        return cluster[database][collection].insert_many(data).inserted_ids

    @staticmethod
    def get_many(query, cluster, database, collection):
        return cluster[database][collection].find(query)

    @staticmethod
    def update_many(query, data, cluster, database, collection):
        return cluster[database][collection].update_many(query, data)

    @staticmethod
    def delete_many(query, cluster, database, collection):
        return cluster[database][collection].delete_many(query)
