from django.db.models.sql.datastructures import Join
from django.db.models.fields.related import ForeignObject


class CompareJoin(Join):
    def __init__(self, table_name, parent_alias, table_alias, join_type,
                 join_field, compare_filed, comparison_sign, nullable, filtered_relation=None):

        super().__init__(table_name, parent_alias, table_alias, join_type, join_field, nullable, filtered_relation)

        self.compare_cols = compare_filed.get_joining_columns()
        self.compare_field = compare_filed
        if comparison_sign in ['<', '>', '=>', '<=']:
            self.sign = comparison_sign
        else:
            raise ValueError(f'"{comparison_sign}" is allowed sign.')

    def as_sql(self, compiler, connection):
        """
        Generate the full
           LEFT OUTER JOIN sometable ON sometable.somecol = othertable.othercol, params
        clause for this join.
        """
        join_conditions = []
        params = []
        qn = compiler.quote_name_unless_alias
        qn2 = connection.ops.quote_name

        # Add a join condition for each pair of joining columns.
        for lhs_col, rhs_col in self.join_cols:
            join_conditions.append('%s.%s = %s.%s' % (
                qn(self.parent_alias),
                qn2(lhs_col),
                qn(self.table_alias),
                qn2(rhs_col),
            ))
        for lhs_col, rhs_col in self.compare_cols:
            join_conditions.append(
                f"{qn(self.parent_alias)}.{qn2(lhs_col)} "
                f"{self.sign} "
                f"{qn(self.table_alias)}.{qn2(rhs_col)}")

        # Add a single condition inside parentheses for whatever
        # get_extra_restriction() returns.
        extra_cond = self.join_field.get_extra_restriction(
            compiler.query.where_class, self.table_alias, self.parent_alias)
        if extra_cond:
            extra_sql, extra_params = compiler.compile(extra_cond)
            join_conditions.append('(%s)' % extra_sql)
            params.extend(extra_params)
        if self.filtered_relation:
            extra_sql, extra_params = compiler.compile(self.filtered_relation)
            if extra_sql:
                join_conditions.append('(%s)' % extra_sql)
                params.extend(extra_params)
        if not join_conditions:
            # This might be a rel on the other end of an actual declared field.
            declared_field = getattr(self.join_field, 'field', self.join_field)
            raise ValueError(
                "Join generated an empty ON clause. %s did not yield either "
                "joining columns or extra restrictions." % declared_field.__class__
            )
        on_clause_sql = ' AND '.join(join_conditions)
        alias_str = '' if self.table_alias == self.table_name else (' %s' % self.table_alias)
        sql = '%s %s%s ON (%s)' % (self.join_type, qn(self.table_name), alias_str, on_clause_sql)
        return sql, params
