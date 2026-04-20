class NavigationMixin:
    """Mixin: Back / Forward navigation with page history and password gating."""

    def go_backward(self):
        if len(self.backward) <= 1:
            return
        self.is_navigating_history = True
        current = self.backward.pop()
        self.forward.append(current)
        target = self.backward[-1]

        if target == self.page_setting:
            if not self.ask_password():
                self.backward.append(current)
                self.forward.pop()
                self.is_navigating_history = False
                return

        self.tabs.setCurrentWidget(target)
        self.is_navigating_history = False
        self.update_tab_navigation_buttons()

    def go_forward(self):
        if not self.forward:
            return
        self.is_navigating_history = True
        target = self.forward.pop()

        if target == self.page_setting:
            if not self.ask_password():
                self.forward.append(target)
                self.is_navigating_history = False
                return

        self.backward.append(target)
        self.tabs.setCurrentWidget(target)
        self.is_navigating_history = False
        self.update_tab_navigation_buttons()

    def on_tab_change(self, index):
        if getattr(self, "_suppress_on_tab_change", False):
            return

        current_widget = self.tabs.widget(index)

        if not self.is_navigating_history:
            if current_widget == self.page_setting:
                if getattr(self, "_skip_next_password_prompt", False):
                    self._skip_next_password_prompt = False
                else:
                    if not self.ask_password():
                        self._suppress_on_tab_change = True
                        last = getattr(self, "_last_selected_widget", self.main_page)
                        self.tabs.setCurrentWidget(last)
                        self._suppress_on_tab_change = False
                        return

            self.backward.append(current_widget)
            self.forward.clear()

        self._last_selected_widget = current_widget

        # Engineer label visibility
        if current_widget in (self.page_setting,):
            self.lbl_engineer.setVisible(True)
        else:
            self.lbl_engineer.setVisible(False)

        self.update_tab_navigation_buttons()

    def update_tab_navigation_buttons(self):
        if hasattr(self, "btn_back"):
            self.btn_back.setEnabled(len(self.backward) > 1)
        if hasattr(self, "btn_forward"):
            self.btn_forward.setEnabled(len(self.forward) > 0)
