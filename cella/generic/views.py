class ForRawQueryViewMixin:
    searching_fields = ()
    ordering_fields = ()

    def searching_expression(self, searching):
        searching_exp = f" LIKE '%{searching}%' OR ".join(self.searching_fields) + f" LIKE '%{searching}%'"
        return searching_exp

    def ordering_expression(self, ordering):
        ordering = ordering.strip(',').split(',')
        order_exp = []
        for ordering_field in ordering:

            if ordering_field.startswith('-'):
                ordering_field = ordering_field.replace('-', '')

                if ordering_field in self.ordering_fields:
                    order_exp.append(f"{ordering_field} DESC")

            if ordering_field in self.ordering_fields:
                order_exp.append(f"{ordering_field}")
        return order_exp
