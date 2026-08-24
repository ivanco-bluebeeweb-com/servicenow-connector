# ServiceNow Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`,
`concepts/panels.md`. Основано на функционале `servicenow-connector`.

## 0. Разница с IDEAL_ONBOARDING.md
Идеал предполагает мгновенную проверку через реальный вызов Table API прямо в форме
подключения. Реализация делает это тем же способом, что и другие OAuth/Basic коннекторы
портфеля (SAP, Oracle) — `connect_servicenow` сам выполняет пробный запрос перед
сохранением, и форма показывает результат через стандартный error/success путь `ui.Form`,
без отдельного разрешения на "предпросмотр перед сохранением" (SDK не имеет отдельного
preview-хука для форм подключения).

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Stack`(v, align="start") + `ui.Text`(instance label) + `ui.Divider` + `ui.Button`×4 (Incidents/Problems/Changes/Requests) + `ui.Button`("App settings") | Без карточек, без дублирования инструкций — паттерн Webflow/MuleSoft. |
| Connect form (sidebar, not connected) | `ui.Form` + `ui.Select`(auth mode: OAuth2/Basic Auth) + labelled `ui.Input`(instance host) + условные поля (client id/secret ИЛИ username/password) + `ui.Button`("How do I get this?" → help dialog) | Select переключает набор полей — оба режима реально поддерживаются по Discovery. |
| Help dialog | `ui.Dialog`/`ui.panel(center_overlay=True)` + `ui.Text`(шаги для OAuth Application Registry и для Basic Auth integration user) | Единственное место с инструкциями подключения. |
| Incidents list (center, `center_overlay=True`) | `ui.Header` + `ui.Select`(priority filter) + `ui.DataTable`(number/short_description/priority/state/assigned_to) + row action `ui.Button`("Open") | Табличный список — стандартный паттерн для списков записей. |
| Incident detail | `ui.Stack`(v) + labelled `ui.Text`×N (полей) + `ui.Form`(action=update_incident: state Select, work_notes Textarea) | Форма обновления с явными лейблами полей. |
| Create incident/problem/change/request | `ui.Form` + labelled `ui.Input`/`ui.Textarea`/`ui.Select` под каждый обязательный + важный опциональный параметр | Полная форма создания записи — не half-baked. |
| Generic table browser (Tier 2) | `ui.Form`(table name Input + query Input) + `ui.CodeBlock`(результат JSON) | Честный passthrough для нетипизированных таблиц, как в Infor. |
| App settings (center, `center_overlay=True`) | `ui.Header` + `ui.Stack`(per-connection: label, host, auth mode badge, Disconnect button) | Единственное место для disconnect. |

## 2. User flow
1. Пустое состояние → `_connect_form()` в sidebar с переключателем режима.
2. `connect_servicenow` вызывает пробный GET к `sys_user?sysparm_limit=1` для
   валидации перед сохранением (как SAP/Oracle паттерн).
3. После подключения — sidebar показывает host + 4 кнопки на основные ITSM-модули
   + App settings.
4. Каждая кнопка модуля открывает center-панель со списком + фильтром + возможностью
   создать новую запись.
5. Detail-экран записи — обновление статуса/полей через `ui.Form`.
6. Disconnect — только в App settings, с подтверждением через стандартный destructive
   button pattern.

## 3. Обоснование выбора примитивов
`ui.DataTable` выбран для списков (не `ui.Card`-список), потому что записи ITSM —
однородные табличные данные с сортировкой/фильтрацией, и `ui.DataTable` — единственный
примитив SDK с построчными action-кнопками без ручной генерации карточек. Формы везде
используют `_field()`-обёртку (лейбл + инпут), контекстно-подходящий placeholder на
каждом поле (например "INC0012345" для номера инцидента, а не generic "Enter value").
