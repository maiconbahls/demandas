    def save_categories(self, categories: Dict) -> bool:
        if self.use_sheets:
            try:
                ws = self._get_worksheet("Categories")
                # Flatten dict to list of dicts for sheet
                data = []
                for key, val in categories.items():
                    item = val.copy()
                    item['key'] = key
                    data.append(item)
                
                if data:
                    ws.clear()
                    ws.append_row(list(data[0].keys()))
                    rows = [list(d.values()) for d in data]
                    ws.append_rows(rows)
                else:
                    ws.clear()
                return True
            except Exception as e:
                st.error(f"Erro ao salvar categorias na nuvem: {e}")
                return False

        # Local
        try:
            with open(self.categories_path, "w", encoding="utf-8") as f:
                json.dump(categories, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            st.error(f"Erro ao salvar categorias localmente: {e}")
            return False
