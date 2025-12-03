"""Aplicativo gráfico para baixar cartas de Magic: The Gathering."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from . import constants as const
from .config_store import load_config, save_config
from .io_helpers import (
    build_image_url_candidates,
    download_binary,
    ensure_output_dir,
    get_color_folder_name,
    get_language_folder_name,
    get_rarity_folder_name,
    get_scryfall_id,
    get_type_folder_name,
    sanitize_filename,
)
from .models import SetMetadata
from .mtgjson import (
    download_allprintings,
    fetch_allprintings_remote_meta,
    load_sets_from_file,
    needs_database_update,
    reset_local_database,
)

class MagicDownloaderApp:

    """Interface gr├ífica para baixar cartas filtradas."""



    def __init__(self, root: tk.Tk) -> None:

        self.root = root

        self.app_language = const.DEFAULT_APP_LANGUAGE

        self.config_data: Dict[str, Any] = load_config()

        self._apply_config_preferences()

        self.root.title(self._t("title"))

        self.root.geometry("960x640")

        self.root.minsize(860, 540)



        self.queue: Queue = Queue()

        self.sets_data: Dict[str, Dict] = {}

        self.sets_metadata: List[SetMetadata] = []

        self.filtered_metadata: List[SetMetadata] = []

        self.database_lock = threading.Lock()

        self.sets_lock = threading.Lock()



        self.destination_var = tk.StringVar(value=str(const.DEFAULT_OUTPUT_DIR))

        self.selected_type_key = const.CARD_TYPE_ORDER[0]

        self.selected_rarity_key = const.RARITY_ORDER[0]

        self.type_var = tk.StringVar()

        self.rarity_var = tk.StringVar()

        self.type_display_to_key: Dict[str, str] = {}

        self.rarity_display_to_key: Dict[str, str] = {}

        self.type_box: Optional[ttk.Combobox] = None

        self.rarity_box: Optional[ttk.Combobox] = None

        self.app_language_button: Optional[ttk.Button] = None

        self.app_language_label: Optional[ttk.Label] = None

        self.filters_frame: Optional[ttk.LabelFrame] = None

        self.sets_frame: Optional[ttk.LabelFrame] = None

        self.btn_clear_sets: Optional[ttk.Button] = None

        self.log_frame: Optional[ttk.LabelFrame] = None

        self.card_type_label: Optional[ttk.Label] = None

        self.rarity_label: Optional[ttk.Label] = None

        self.name_contains_label: Optional[ttk.Label] = None

        self.set_filter_label: Optional[ttk.Label] = None

        self.image_language_label: Optional[ttk.Label] = None

        self.btn_choose_dest: Optional[ttk.Button] = None

        self.language_box: Optional[ttk.Combobox] = None

        self.name_filter_var = tk.StringVar()

        self.set_filter_var = tk.StringVar()

        self.language_display_to_code: Dict[str, str] = {}

        self.language_options: List[str] = []

        self.language_var = tk.StringVar()

        self._refresh_language_choices(preserve_selected_code=False)

        self.status_var = tk.StringVar(value=self._t("status_ready"))

        self.progress_var = tk.DoubleVar(value=0.0)

        self.progress_label_var = tk.StringVar(value="0%")

        self.btn_stop_download: Optional[ttk.Button] = None

        self.download_cancel_event = threading.Event()

        self.is_downloading = False



        self._build_ui()

        self.root.after(150, self._process_queue)

        threading.Thread(target=self._auto_bootstrap_task, daemon=True).start()



    def _build_ui(self) -> None:

        control_frame = ttk.Frame(self.root, padding=10)

        control_frame.pack(fill=tk.X)



        self.btn_download_db = ttk.Button(

            control_frame,

            text=self._t("download_db"),

            command=self.download_database,

        )

        self.btn_download_db.pack(side=tk.LEFT, padx=(0, 6))



        self.btn_load_sets = ttk.Button(

            control_frame,

            text=self._t("load_sets"),

            command=self.load_sets,

        )

        self.btn_load_sets.pack(side=tk.LEFT, padx=(0, 6))



        self.btn_choose_dest = ttk.Button(

            control_frame,

            text=self._t("choose_dest"),

            command=self.choose_directory,

        )

        self.btn_choose_dest.pack(side=tk.LEFT)



        ttk.Label(control_frame, textvariable=self.destination_var).pack(

            side=tk.LEFT, padx=10

        )



        self.filters_frame = ttk.LabelFrame(self.root, text=self._t("filters"), padding=10)

        self.filters_frame.pack(fill=tk.X, padx=10, pady=5)



        self.card_type_label = ttk.Label(self.filters_frame, text=self._t("card_type"))

        self.card_type_label.grid(row=0, column=0, sticky=tk.W)

        self.type_box = ttk.Combobox(

            self.filters_frame,

            textvariable=self.type_var,

            state="readonly",

            width=28,

            values=[],

        )

        self.type_box.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)

        self.type_box.bind("<<ComboboxSelected>>", self._on_type_selected)



        self.rarity_label = ttk.Label(self.filters_frame, text=self._t("rarity"))

        self.rarity_label.grid(row=0, column=2, sticky=tk.W)

        self.rarity_box = ttk.Combobox(

            self.filters_frame,

            textvariable=self.rarity_var,

            state="readonly",

            width=24,

            values=[],

        )

        self.rarity_box.grid(row=0, column=3, padx=5, pady=2, sticky=tk.W)

        self.rarity_box.bind("<<ComboboxSelected>>", self._on_rarity_selected)



        self.name_contains_label = ttk.Label(self.filters_frame, text=self._t("name_contains"))

        self.name_contains_label.grid(row=1, column=0, sticky=tk.W)

        ttk.Entry(self.filters_frame, textvariable=self.name_filter_var, width=30).grid(

            row=1, column=1, padx=5, pady=2, sticky=tk.W

        )



        self.set_filter_label = ttk.Label(self.filters_frame, text=self._t("set_filter"))

        self.set_filter_label.grid(row=1, column=2, sticky=tk.W)

        set_filter_entry = ttk.Entry(self.filters_frame, textvariable=self.set_filter_var, width=24)

        set_filter_entry.grid(row=1, column=3, padx=5, pady=2, sticky=tk.W)

        set_filter_entry.bind("<KeyRelease>", lambda _event: self._refresh_set_list())



        self.image_language_label = ttk.Label(self.filters_frame, text=self._t("image_language"))

        self.image_language_label.grid(row=2, column=0, sticky=tk.W, pady=(6, 0))

        self.language_box = ttk.Combobox(

            self.filters_frame,

            textvariable=self.language_var,

            values=self.language_options,

            state="readonly",

            width=30,

        )

        self.language_box.grid(row=2, column=1, padx=5, pady=(6, 0), sticky=tk.W)



        self.app_language_label = ttk.Label(self.filters_frame, text=self._t("app_language"))

        self.app_language_label.grid(row=2, column=2, sticky=tk.W, pady=(6, 0))

        self.app_language_button = ttk.Button(

            self.filters_frame,

            text=self._get_app_language_label(),

            command=self._toggle_app_language,

            width=20,

        )

        self.app_language_button.grid(row=2, column=3, padx=5, pady=(6, 0), sticky=tk.W)



        self.sets_frame = ttk.LabelFrame(self.root, text=self._t("sets"), padding=10)

        self.sets_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)



        sets_header = ttk.Frame(self.sets_frame)

        sets_header.pack(fill=tk.X, side=tk.TOP, anchor=tk.W, pady=(0, 6))

        self.btn_clear_sets = ttk.Button(

            sets_header,

            text=self._t("clear_selection"),

            command=self.clear_set_selection,

        )

        self.btn_clear_sets.pack(side=tk.RIGHT)



        self.set_list = tk.Listbox(self.sets_frame, selectmode=tk.MULTIPLE, exportselection=False)

        self.set_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)



        scrollbar = ttk.Scrollbar(self.sets_frame, orient=tk.VERTICAL, command=self.set_list.yview)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.set_list.config(yscrollcommand=scrollbar.set)



        action_frame = ttk.Frame(self.root, padding=10)

        action_frame.pack(fill=tk.X)



        self.btn_start_download = ttk.Button(

            action_frame,

            text=self._t("download_cards"),

            command=self.start_download,

            state=tk.DISABLED,

        )

        self.btn_start_download.pack(side=tk.LEFT)



        self.btn_stop_download = ttk.Button(

            action_frame,

            text=self._t("stop_download"),

            command=self.stop_download,

            state=tk.DISABLED,

        )

        self.btn_stop_download.pack(side=tk.LEFT, padx=(6, 0))



        ttk.Progressbar(

            action_frame,

            variable=self.progress_var,

            maximum=100.0,

            length=320,

        ).pack(side=tk.LEFT, padx=10)



        ttk.Label(action_frame, textvariable=self.progress_label_var, width=18, anchor=tk.W).pack(side=tk.LEFT)

        ttk.Label(action_frame, textvariable=self.status_var).pack(side=tk.LEFT)



        self.log_frame = ttk.LabelFrame(self.root, text=self._t("log"), padding=10)

        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))



        self.log_widget = scrolledtext.ScrolledText(self.log_frame, height=10, state=tk.DISABLED)

        self.log_widget.pack(fill=tk.BOTH, expand=True)



        self._apply_language_to_ui()



    def _get_card_type_label(self, key: str) -> str:

        return const.CARD_TYPE_LABELS.get(key, {}).get(self.app_language, key)



    def _get_rarity_label(self, key: str) -> str:

        return const.RARITY_LABELS.get(key, {}).get(self.app_language, key)


    def _get_next_app_language_code(self) -> str:
        codes = list(const.APP_LANGUAGES.keys())
        if self.app_language in codes:
            index = codes.index(self.app_language)
            return codes[(index + 1) % len(codes)]
        return const.DEFAULT_APP_LANGUAGE



    def _get_app_language_label(self, code: Optional[str] = None) -> str:
        target_code = code or self.app_language
        return const.APP_LANGUAGES.get(target_code, target_code.upper())



    def _t(self, key: str, **kwargs: Any) -> str:

        language_pack = const.TEXTS.get(self.app_language) or const.TEXTS.get(const.DEFAULT_APP_LANGUAGE) or {}

        fallback_pack = const.TEXTS.get(const.DEFAULT_APP_LANGUAGE, {})

        template = language_pack.get(key) or fallback_pack.get(key) or key

        if kwargs:

            try:

                return template.format(**kwargs)

            except KeyError:

                return template

        return template



    def _apply_language_to_ui(self) -> None:

        self._refresh_filter_comboboxes()
        self._refresh_language_choices()

        if self.btn_download_db:

            self.btn_download_db.config(text=self._t("download_db"))

        if self.btn_load_sets:

            self.btn_load_sets.config(text=self._t("load_sets"))

        if self.btn_choose_dest:

            self.btn_choose_dest.config(text=self._t("choose_dest"))

        if self.filters_frame:

            self.filters_frame.config(text=self._t("filters"))

        if self.card_type_label:

            self.card_type_label.config(text=self._t("card_type"))

        if self.rarity_label:

            self.rarity_label.config(text=self._t("rarity"))

        if self.name_contains_label:

            self.name_contains_label.config(text=self._t("name_contains"))

        if self.set_filter_label:

            self.set_filter_label.config(text=self._t("set_filter"))

        if self.image_language_label:

            self.image_language_label.config(text=self._t("image_language"))

        if self.app_language_label:

            self.app_language_label.config(text=self._t("app_language"))

        if self.sets_frame:

            self.sets_frame.config(text=self._t("sets"))

        if self.btn_clear_sets:

            self.btn_clear_sets.config(text=self._t("clear_selection"))

        if self.log_frame:

            self.log_frame.config(text=self._t("log"))

        if self.btn_start_download:

            self.btn_start_download.config(text=self._t("download_cards"))

        if self.btn_stop_download:

            self.btn_stop_download.config(text=self._t("stop_download"))

        if self.app_language_button:

            self.app_language_button.config(text=self._get_app_language_label())

        self.root.title(self._t("title"))



    def _toggle_app_language(self) -> None:

        new_code = self._get_next_app_language_code()

        if new_code == self.app_language:

            return

        self.app_language = new_code

        self._persist_config()

        self._apply_language_to_ui()



    def _apply_config_preferences(self) -> None:

        stored_language = str(self.config_data.get("app_language", "")).lower()

        if stored_language in const.APP_LANGUAGES:

            self.app_language = stored_language



    def _persist_config(self) -> None:

        payload = dict(self.config_data)

        payload["app_language"] = self.app_language

        self.config_data = payload

        save_config(payload)



    def _refresh_filter_comboboxes(self) -> None:

        type_values: List[str] = []

        self.type_display_to_key.clear()

        for key in const.CARD_TYPE_ORDER:

            label = self._get_card_type_label(key)

            type_values.append(label)

            self.type_display_to_key[label] = key

        if self.type_box is not None:

            self.type_box["values"] = type_values

        self.type_var.set(self._get_card_type_label(self.selected_type_key))



        rarity_values: List[str] = []

        self.rarity_display_to_key.clear()

        for key in const.RARITY_ORDER:

            label = self._get_rarity_label(key)

            rarity_values.append(label)

            self.rarity_display_to_key[label] = key

        if self.rarity_box is not None:

            self.rarity_box["values"] = rarity_values

        self.rarity_var.set(self._get_rarity_label(self.selected_rarity_key))


    def _refresh_language_choices(self, preserve_selected_code: bool = True) -> None:

        previous_code = None

        if preserve_selected_code and self.language_display_to_code:

            previous_code = self.language_display_to_code.get(self.language_var.get())

        display_map = const.get_language_display_map(self.app_language)

        if not display_map:

            display_map = {"English (EN)": "en"}

        self.language_display_to_code = display_map

        self.language_options = list(display_map.keys())

        if self.language_box is not None:

            self.language_box["values"] = self.language_options

        target_code = previous_code or "en"

        selection = next((label for label, code in display_map.items() if code == target_code), None)

        if selection is None and self.language_options:

            selection = self.language_options[0]

        if selection:

            self.language_var.set(selection)



    def _on_type_selected(self, _event: Optional[tk.Event] = None) -> None:

        label = self.type_var.get()

        if self.type_display_to_key:

            self.selected_type_key = self.type_display_to_key.get(label, const.CARD_TYPE_ORDER[0])

        else:

            self.selected_type_key = const.CARD_TYPE_ORDER[0]

        if label not in self.type_display_to_key:

            self.type_var.set(self._get_card_type_label(self.selected_type_key))



    def _on_rarity_selected(self, _event: Optional[tk.Event] = None) -> None:

        label = self.rarity_var.get()

        if self.rarity_display_to_key:

            self.selected_rarity_key = self.rarity_display_to_key.get(label, const.RARITY_ORDER[0])

        else:

            self.selected_rarity_key = const.RARITY_ORDER[0]

        if label not in self.rarity_display_to_key:

            self.rarity_var.set(self._get_rarity_label(self.selected_rarity_key))



    def choose_directory(self) -> None:

        selected = filedialog.askdirectory(initialdir=self.destination_var.get())

        if selected:

            self.destination_var.set(selected)



    def download_database(self) -> None:

        thread = threading.Thread(target=self._download_database_task, daemon=True)

        thread.start()



    def _download_database_task(
        self,
        remote_meta: Optional[Dict[str, Any]] = None,
        auto_load_after: bool = False,
    ) -> None:

        if not self.database_lock.acquire(blocking=False):

            self.queue.put(("log", self._t("download_in_progress")))

            return

        download_success = False

        try:
            remote_meta = remote_meta or fetch_allprintings_remote_meta()

            if not const.ALL_PRINTINGS_FILE.parent.exists():
                const.ALL_PRINTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

            self.queue.put(("status", self._t("status_downloading_db")))
            self.queue.put(("log", self._t("log_db_start")))

            def progress_hook(percent: float, speed: float) -> None:
                label = f"{percent:5.1f}% ({speed:.2f} MB/s)"
                self.queue.put(("progress", {"value": percent, "label": label}))

            success, error_message = download_allprintings(remote_meta, progress_hook=progress_hook)
            if success:
                download_success = True
                self.queue.put(("log", self._t("log_db_done_hint")))
            else:
                error_text = error_message or self._t("error_unknown")
                self.queue.put(("error", self._t("error_db_download", error=error_text)))
        finally:
            self.queue.put(("status", self._t("status_ready")))
            self.queue.put(("progress", 0.0))
            self.database_lock.release()



        if auto_load_after and download_success:

            threading.Thread(target=self._load_sets_task, daemon=True).start()



    def load_sets(self) -> None:

        if not const.ALL_PRINTINGS_FILE.exists():

            messagebox.showwarning(self._t("warning_title"), self._t("missing_allprintings"))

            return



        self.btn_load_sets.config(state=tk.DISABLED)

        thread = threading.Thread(target=self._load_sets_task, daemon=True)

        thread.start()



    def _load_sets_task(self) -> None:

        if not self.sets_lock.acquire(blocking=False):

            self.queue.put(("log", self._t("log_sets_in_progress")))

            return



        self.queue.put(("status", self._t("sets_loading")))

        try:

            data, metadata = load_sets_from_file()

            self.queue.put(("sets_loaded", (data, metadata)))

            self.queue.put(("log", self._t("sets_loaded", count=len(metadata))))

        except (OSError, ValueError) as exc:

            self.queue.put(("error", self._t("error_load_sets", error=exc)))

            self._handle_corrupted_database()

        finally:

            self.queue.put(("status", self._t("status_ready")))

            self.queue.put(("progress", 0.0))

            self.sets_lock.release()



    def _handle_corrupted_database(self) -> None:
        reset_local_database()

        self.queue.put(("log", self._t("log_db_corrupted")))
        self.queue.put(("log", self._t("log_db_redownload")))

        threading.Thread(

            target=self._download_database_task,

            kwargs={"auto_load_after": True},

            daemon=True,

        ).start()



    def _on_sets_loaded(self, data: Dict, metadata: List[SetMetadata]) -> None:

        self.sets_data = data

        self.sets_metadata = metadata

        self.filtered_metadata = metadata

        self._refresh_set_list()

        self.btn_start_download.config(state=tk.NORMAL)

        self.btn_load_sets.config(state=tk.NORMAL)



    def _refresh_set_list(self) -> None:

        filter_text = self.set_filter_var.get().lower().strip()

        if filter_text:

            self.filtered_metadata = [item for item in self.sets_metadata if filter_text in item.search]

        else:

            self.filtered_metadata = list(self.sets_metadata)



        self.set_list.delete(0, tk.END)

        for item in self.filtered_metadata:

            display = f"[{item.code}] {item.name} ({item.release})"

            self.set_list.insert(tk.END, display)



    def clear_set_selection(self) -> None:

        if self.set_list is not None:

            self.set_list.selection_clear(0, tk.END)



    def stop_download(self) -> None:

        if not self.is_downloading:

            return

        self.download_cancel_event.set()

        if self.btn_stop_download:

            self.btn_stop_download.config(state=tk.DISABLED)



    def _on_download_complete(self, canceled: bool) -> None:

        self.is_downloading = False

        if self.btn_stop_download:
            self.btn_stop_download.config(state=tk.DISABLED)
        if self.btn_start_download:
            state = tk.NORMAL if self.sets_data else tk.DISABLED
            self.btn_start_download.config(state=state)
    def start_download(self) -> None:
        if not self.sets_data:

            messagebox.showinfo(self._t("info_title"), self._t("missing_sets"))

            return



        selection = self.set_list.curselection()

        if not selection:

            messagebox.showwarning(self._t("warning_title"), self._t("missing_selection"))

            return



        selected_codes = [self.filtered_metadata[idx].code for idx in selection]

        destination = Path(self.destination_var.get()).expanduser()



        type_key = self.selected_type_key

        rarity_key = self.selected_rarity_key

        name_filter = self.name_filter_var.get().strip().lower()

        language_display = self.language_var.get()

        language_code = self.language_display_to_code.get(language_display, "en")



        self.is_downloading = True

        self.download_cancel_event.clear()

        if self.btn_start_download:

            self.btn_start_download.config(state=tk.DISABLED)

        if self.btn_stop_download:

            self.btn_stop_download.config(state=tk.NORMAL)



        thread = threading.Thread(

            target=self._download_sets_task,

            args=(selected_codes, destination, type_key, rarity_key, name_filter, language_code),

            daemon=True,

        )

        thread.start()



    def _filter_cards(

        self,

        set_codes: List[str],

        type_key: str,

        rarity_key: str,

        name_filter: str,

    ) -> tuple[Dict[str, List[Dict]], int]:

        type_rule = const.CARD_TYPE_RULES.get(type_key, const.CARD_TYPE_RULES["all"])

        rarity_value = const.RARITY_VALUES.get(rarity_key)

        normalized_name = name_filter.strip().lower()



        filtered_cards: Dict[str, List[Dict]] = {}

        total_cards = 0



        for code in set_codes:

            set_info = self.sets_data.get(code, {})

            cards = set_info.get("cards", [])

            selected = [

                card

                for card in cards

                if type_rule(card)

                and (not rarity_value or card.get("rarity") == rarity_value)

                and (not normalized_name or normalized_name in card.get("name", "").lower())

                and get_scryfall_id(card)

            ]

            if selected:

                filtered_cards[code] = selected

                total_cards += len(selected)



        return filtered_cards, total_cards



    def _download_sets_task(

        self,

        set_codes: List[str],

        destination: Path,

        type_key: str,

        rarity_key: str,

        name_filter: str,

        language_code: str,

        prepared_cards: Optional[Dict[str, List[Dict]]] = None,

        prepared_total: Optional[int] = None,

    ) -> None:

        self.queue.put(("status", self._t("status_filtering")))

        ensure_output_dir(destination)



        filtered_cards = prepared_cards

        total_cards = prepared_total

        cancel_event = self.download_cancel_event



        if filtered_cards is None or total_cards is None:

            filtered_cards, total_cards = self._filter_cards(set_codes, type_key, rarity_key, name_filter)



        if total_cards == 0:

            self.queue.put(("error", self._t("error_no_cards")))

            self.queue.put(("status", self._t("status_ready")))

            self.queue.put(("progress", 0.0))

            self.queue.put(("download_complete", {"canceled": True}))

            return



        if total_cards >= const.CARD_WARNING_THRESHOLD:

            confirmation_event = threading.Event()

            decision_holder: Dict[str, bool] = {"proceed": False}

            estimated_gb = (total_cards * const.CARD_WARNING_MB_PER_IMAGE) / 1024

            self.queue.put(

                (

                    "confirm_download",

                    (total_cards, estimated_gb, confirmation_event, decision_holder),

                )

            )

            confirmation_event.wait()



            if not decision_holder.get("proceed"):

                self.queue.put(("log", self._t("log_download_cancelled")))

                self.queue.put(("status", self._t("status_ready")))

                self.queue.put(("progress", 0.0))

                self.queue.put(("download_complete", {"canceled": True}))

                return



        self.queue.put(("status", self._t("status_downloading_cards", total=total_cards)))

        self.queue.put(("log", self._t("download_log_start", cards=total_cards)))



        downloaded = 0

        canceled = False

        language_primary_failures: Dict[str, int] = {}

        for code, cards in filtered_cards.items():

            if cancel_event.is_set():

                canceled = True

                break

            set_name = self.sets_data.get(code, {}).get("name", code)

            folder_name = sanitize_filename(f"{code}_{set_name}") or code

            set_folder = ensure_output_dir(destination / folder_name)

            language_folder = ensure_output_dir(
                set_folder / get_language_folder_name(language_code, self.app_language)
            )



            for card in cards:

                if cancel_event.is_set():

                    canceled = True

                    break

                card_name = sanitize_filename(card.get("name", "carta"))

                card_number = card.get("number")

                filename = f"{card_number}_{card_name}" if card_number else card_name

                color_folder = ensure_output_dir(
                    language_folder / get_color_folder_name(card, self.app_language)
                )
                type_folder = ensure_output_dir(
                    color_folder / get_type_folder_name(card, self.app_language)
                )
                rarity_folder = ensure_output_dir(
                    type_folder / get_rarity_folder_name(card.get("rarity"), self.app_language)
                )

                primary_path = rarity_folder / f"{filename}.png"

                fallback_path = rarity_folder / f"{filename}_EN.png"



                if primary_path.exists() or fallback_path.exists():

                    downloaded += 1

                    percent = (downloaded / total_cards) * 100

                    label = self._t(

                        "progress_cards_label",

                        percent=f"{percent:5.1f}",

                        downloaded=downloaded,

                        total=total_cards,

                    )

                    self.queue.put(("progress", {"value": percent, "label": label}))

                    continue



                url_candidates = build_image_url_candidates(card, code, language_code)

                lang_label = language_code.upper()
                selected_language = language_code.lower()
                skip_primary_language = (
                    selected_language != "en"
                    and language_primary_failures.get(code, 0) >= const.LANGUAGE_AUTO_FALLBACK_THRESHOLD
                )

                card_display_name = card.get("name") or self._t("card_fallback_name")

                success = False

                fallback_used = False

                attempts_made = 0

                last_error: Optional[str] = None

                last_lang_label = lang_label



                for idx, url in enumerate(url_candidates):

                    is_fallback_attempt = idx > 0 and selected_language != "en"
                    is_primary_language_attempt = selected_language != "en" and not is_fallback_attempt

                    if is_primary_language_attempt and skip_primary_language:
                        continue

                    attempt_lang_label = "EN" if is_fallback_attempt else lang_label

                    target_path = fallback_path if is_fallback_attempt else primary_path



                    for attempt in range(1, const.IMAGE_DOWNLOAD_RETRIES + 1):

                        attempts_made += 1

                        success, error_message = download_binary(url, target_path)

                        if success:

                            fallback_used = is_fallback_attempt

                            last_error = None

                            break



                        last_error = error_message or self._t("error_unknown")

                        last_lang_label = attempt_lang_label

                        is_not_found = bool(error_message and "status 404" in error_message.lower())

                        log_retry = True

                        if is_not_found and is_primary_language_attempt:

                            failure_count = language_primary_failures.get(code, 0) + 1

                            language_primary_failures[code] = failure_count

                            if failure_count == const.LANGUAGE_AUTO_FALLBACK_THRESHOLD:

                                self.queue.put(

                                    (

                                        "log",

                                        self._t(

                                            "log_language_unavailable",

                                            lang=lang_label,

                                            set_name=set_name,

                                        ),

                                    )

                                )

                            log_retry = False

                        if log_retry:

                            self.queue.put(

                                (

                                    "log",

                                    self._t(

                                        "log_download_retry",

                                        attempt=attempt,

                                        total=const.IMAGE_DOWNLOAD_RETRIES,

                                        lang=attempt_lang_label,

                                        set_name=set_name,

                                        card_name=card_display_name,

                                        error=last_error,

                                    ),

                                )

                            )

                        if is_not_found or attempt == const.IMAGE_DOWNLOAD_RETRIES:

                            break

                        time.sleep(const.IMAGE_RETRY_DELAY)



                    if success:

                        break

                if success:

                    if fallback_used:

                        self.queue.put(

                            (

                                "log",

                                self._t(

                                    "log_download_fallback",

                                    set_name=set_name,

                                    card_name=card_display_name,

                                ),

                            )

                        )

                    else:

                        self.queue.put(

                            (

                                "log",

                                self._t(

                                    "log_download_success",

                                    lang=lang_label,

                                    set_name=set_name,

                                    card_name=card_display_name,

                                ),

                            )

                        )

                else:

                    self.queue.put(

                        (

                            "log",

                            self._t(

                                "log_download_failure",

                                lang=last_lang_label,

                                set_name=set_name,

                                card_name=card_display_name,

                                attempts=max(attempts_made, 1),

                                error=last_error or self._t("error_unknown"),

                            ),

                        )

                    )



                downloaded += 1

                percent = (downloaded / total_cards) * 100

                label = self._t(

                    "progress_cards_label",

                    percent=f"{percent:5.1f}",

                    downloaded=downloaded,

                    total=total_cards,

                )

                self.queue.put(("progress", {"value": percent, "label": label}))

                time.sleep(const.REQUEST_DELAY)



            if canceled:

                break



        if canceled:

            self.queue.put(("log", self._t("log_download_stopped")))

        else:

            self.queue.put(("log", self._t("download_log_done")))

        self.queue.put(("status", self._t("status_ready")))

        self.queue.put(("progress", 0.0))

        self.queue.put(("download_complete", {"canceled": canceled}))



    def _process_queue(self) -> None:

        try:

            while True:

                message, payload = self.queue.get_nowait()

                if message == "log":

                    self._append_log(str(payload))

                elif message == "status":

                    self.status_var.set(str(payload))

                elif message == "progress":

                    value: float

                    label_text: Optional[str] = None

                    if isinstance(payload, dict):

                        value = float(payload.get("value", 0.0))

                        label_text = payload.get("label")

                    else:

                        value = float(payload)

                    self.progress_var.set(value)

                    if label_text is None:

                        label_text = f"{value:5.1f}%"

                    self.progress_label_var.set(label_text)

                elif message == "sets_loaded":

                    data, metadata = payload

                    self._on_sets_loaded(data, metadata)

                elif message == "error":

                    messagebox.showerror(self._t("error_title"), str(payload))

                elif message == "confirm_download":

                    total_cards, estimated_gb, event, decision_holder = payload

                    proceed = False

                    try:

                        proceed = messagebox.askyesno(

                            self._t("download_large_title"),

                            self._t("download_large_text", cards=total_cards, gb=estimated_gb),

                        )

                    finally:

                        decision_holder["proceed"] = bool(proceed)

                        event.set()

                elif message == "download_complete":

                    canceled = False

                    if isinstance(payload, dict):

                        canceled = bool(payload.get("canceled"))
                    else:
                        canceled = bool(payload)
                    self._on_download_complete(canceled)
        except Empty:
            pass
        finally:
            self.root.after(150, self._process_queue)
    def _auto_bootstrap_task(self) -> None:
        remote_meta = fetch_allprintings_remote_meta()
        if remote_meta is None:
            self.queue.put(("log", self._t("meta_fail")))
        if needs_database_update(remote_meta):
            self._download_database_task(remote_meta=remote_meta)
        if const.ALL_PRINTINGS_FILE.exists():
            self._load_sets_task()



    def _append_log(self, text: str) -> None:
        self.log_widget.configure(state=tk.NORMAL)
        self.log_widget.insert(tk.END, f"{text}\n")
        self.log_widget.see(tk.END)
        self.log_widget.configure(state=tk.DISABLED)

def main() -> None:
    root = tk.Tk()
    MagicDownloaderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
