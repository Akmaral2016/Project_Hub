"""
============================================================
💼 PROJECTHUB
Advanced Project Management System

Manage. Build. Achieve. 🚀
============================================================

Features:
- OOP
- CRUD
- Validation
- Search
- Sort & Filter
- Statistics
- JSON Storage
- SQLite Database
- CSV Export
- JSON Export / Import
- Backup
- Logging
- Error Handling
- Testing
- Deadline Tracking
- Progress Tracking
- Clean CLI
============================================================
"""

import csv
import json
import logging
import shutil
import sqlite3
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path


# ============================================================
# ⚙️ CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backups"
EXPORT_DIR = BASE_DIR / "exports"
LOG_DIR = BASE_DIR / "logs"

JSON_FILE = DATA_DIR / "projects.json"
DATABASE_FILE = DATA_DIR / "projecthub.db"
LOG_FILE = LOG_DIR / "projecthub.log"

DATE_FORMAT = "%Y-%m-%d"

STATUSES = [
    "Planned",
    "In Progress",
    "Completed",
    "On Hold"
]

PRIORITIES = [
    "Low",
    "Medium",
    "High",
    "Critical"
]

for folder in [
    DATA_DIR,
    BACKUP_DIR,
    EXPORT_DIR,
    LOG_DIR
]:
    folder.mkdir(exist_ok=True)


# ============================================================
# 📝 LOGGER
# ============================================================

logger = logging.getLogger("PROJECTHUB")
logger.setLevel(logging.INFO)

if not logger.handlers:

    file_handler = logging.FileHandler(
        LOG_FILE,
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


# ============================================================
# 📦 PROJECT MODEL
# ============================================================

@dataclass
class Project:

    id: int
    name: str
    description: str
    category: str
    status: str
    priority: str
    deadline: str
    progress: int = 0
    created_at: str = None

    def __post_init__(self):

        if self.created_at is None:
            self.created_at = str(date.today())

    def to_dict(self):

        return asdict(self)

    @classmethod
    def from_dict(cls, data):

        return cls(
            id=int(data["id"]),
            name=data["name"],
            description=data["description"],
            category=data["category"],
            status=data["status"],
            priority=data["priority"],
            deadline=data["deadline"],
            progress=int(data.get("progress", 0)),
            created_at=data.get("created_at")
        )


# ============================================================
# 🗄️ DATABASE
# ============================================================

class Database:

    def __init__(self):

        self.connection = sqlite3.connect(
            DATABASE_FILE
        )

        self.connection.row_factory = sqlite3.Row

        self.create_table()

    # ========================================================
    # 🏗️ CREATE TABLE
    # ========================================================

    def create_table(self):

        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                deadline TEXT NOT NULL,
                progress INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        self.connection.commit()

    # ========================================================
    # ➕ INSERT
    # ========================================================

    def insert(self, project):

        self.connection.execute("""
            INSERT OR REPLACE INTO projects
            (
                id,
                name,
                description,
                category,
                status,
                priority,
                deadline,
                progress,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project.id,
            project.name,
            project.description,
            project.category,
            project.status,
            project.priority,
            project.deadline,
            project.progress,
            project.created_at
        ))

        self.connection.commit()

    # ========================================================
    # 📋 GET ALL
    # ========================================================

    def get_all(self):

        rows = self.connection.execute("""
            SELECT *
            FROM projects
            ORDER BY id
        """).fetchall()

        return [
            self.row_to_project(row)
            for row in rows
        ]

    # ========================================================
    # 🔎 GET BY ID
    # ========================================================

    def get_by_id(self, project_id):

        row = self.connection.execute("""
            SELECT *
            FROM projects
            WHERE id = ?
        """, (project_id,)).fetchone()

        if row is None:
            return None

        return self.row_to_project(row)

    # ========================================================
    # ✏️ UPDATE
    # ========================================================

    def update(self, project):

        self.connection.execute("""
            UPDATE projects

            SET
                name = ?,
                description = ?,
                category = ?,
                status = ?,
                priority = ?,
                deadline = ?,
                progress = ?

            WHERE id = ?
        """, (
            project.name,
            project.description,
            project.category,
            project.status,
            project.priority,
            project.deadline,
            project.progress,
            project.id
        ))

        self.connection.commit()

    # ========================================================
    # 🗑️ DELETE
    # ========================================================

    def delete(self, project_id):

        cursor = self.connection.execute("""
            DELETE FROM projects
            WHERE id = ?
        """, (project_id,))

        self.connection.commit()

        return cursor.rowcount > 0

    # ========================================================
    # 🔍 SEARCH
    # ========================================================

    def search(self, keyword):

        keyword = f"%{keyword.lower()}%"

        rows = self.connection.execute("""
            SELECT *
            FROM projects

            WHERE
                LOWER(name) LIKE ?
                OR LOWER(description) LIKE ?
                OR LOWER(category) LIKE ?

            ORDER BY id
        """, (
            keyword,
            keyword,
            keyword
        )).fetchall()

        return [
            self.row_to_project(row)
            for row in rows
        ]

    # ========================================================
    # 🔄 ROW → PROJECT
    # ========================================================

    @staticmethod
    def row_to_project(row):

        return Project(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            category=row["category"],
            status=row["status"],
            priority=row["priority"],
            deadline=row["deadline"],
            progress=row["progress"],
            created_at=row["created_at"]
        )

    # ========================================================
    # 🧹 CLOSE
    # ========================================================

    def close(self):

        self.connection.close()


# ============================================================
# 🧠 PROJECT SERVICE
# ============================================================

class ProjectService:

    def __init__(self):

        self.database = Database()

        self.sync_json_from_database()

    # ========================================================
    # 🔢 GENERATE ID
    # ========================================================

    def generate_id(self):

        projects = self.database.get_all()

        if not projects:
            return 1

        return max(
            project.id
            for project in projects
        ) + 1

    # ========================================================
    # ➕ CREATE
    # ========================================================

    def create_project(
        self,
        name,
        description,
        category,
        status,
        priority,
        deadline,
        progress
    ):

        validate_text(name, "Project name")
        validate_text(description, "Description")
        validate_text(category, "Category")

        validate_status(status)
        validate_priority(priority)
        validate_date(deadline)
        validate_progress(progress)

        project = Project(
            id=self.generate_id(),
            name=name.strip(),
            description=description.strip(),
            category=category.strip(),
            status=status,
            priority=priority,
            deadline=deadline,
            progress=int(progress)
        )

        self.database.insert(project)

        self.save_json()

        logger.info(
            "Created project ID=%s name=%s",
            project.id,
            project.name
        )

        return project

    # ========================================================
    # 📋 GET ALL
    # ========================================================

    def get_projects(self):

        return self.database.get_all()

    # ========================================================
    # 🔎 GET
    # ========================================================

    def get_project(self, project_id):

        return self.database.get_by_id(
            project_id
        )

    # ========================================================
    # 🔍 SEARCH
    # ========================================================

    def search_projects(self, keyword):

        return self.database.search(
            keyword
        )

    # ========================================================
    # ✏️ UPDATE
    # ========================================================

    def update_project(self, project):

        validate_text(
            project.name,
            "Project name"
        )

        validate_text(
            project.description,
            "Description"
        )

        validate_text(
            project.category,
            "Category"
        )

        validate_status(project.status)
        validate_priority(project.priority)
        validate_date(project.deadline)
        validate_progress(project.progress)

        self.database.update(project)

        self.save_json()

        logger.info(
            "Updated project ID=%s",
            project.id
        )

    # ========================================================
    # 🗑️ DELETE
    # ========================================================

    def delete_project(self, project_id):

        deleted = self.database.delete(
            project_id
        )

        if deleted:

            self.save_json()

            logger.info(
                "Deleted project ID=%s",
                project_id
            )

        return deleted

    # ========================================================
    # 💾 SAVE JSON
    # ========================================================

    def save_json(self):

        projects = self.database.get_all()

        data = [
            project.to_dict()
            for project in projects
        ]

        try:

            with open(
                JSON_FILE,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    data,
                    file,
                    indent=4,
                    ensure_ascii=False
                )

        except OSError as error:

            logger.error(
                "JSON save error: %s",
                error
            )

            raise

    # ========================================================
    # 📥 LOAD JSON
    # ========================================================

    def load_json(self):

        if not JSON_FILE.exists():

            return []

        try:

            with open(
                JSON_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

            return [
                Project.from_dict(item)
                for item in data
            ]

        except (
            OSError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError
        ) as error:

            logger.error(
                "JSON load error: %s",
                error
            )

            return []

    # ========================================================
    # 🔄 SYNC DATABASE → JSON
    # ========================================================

    def sync_json_from_database(self):

        projects = self.database.get_all()

        if projects:

            self.save_json()

    # ========================================================
    # 📥 IMPORT JSON
    # ========================================================

    def import_json(self):

        projects = self.load_json()

        imported = 0

        for project in projects:

            existing = self.get_project(
                project.id
            )

            if existing is None:

                self.database.insert(project)

                imported += 1

        self.save_json()

        logger.info(
            "Imported %s projects",
            imported
        )

        return imported

    # ========================================================
    # 📦 BACKUP
    # ========================================================

    def create_backup(self):

        self.save_json()

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        backup_file = (
            BACKUP_DIR
            / f"projects_backup_{timestamp}.json"
        )

        shutil.copy2(
            JSON_FILE,
            backup_file
        )

        logger.info(
            "Backup created: %s",
            backup_file
        )

        return backup_file

    # ========================================================
    # 📄 CSV EXPORT
    # ========================================================

    def export_csv(self):

        projects = self.get_projects()

        csv_file = (
            EXPORT_DIR
            / "projects.csv"
        )

        fields = [
            "id",
            "name",
            "description",
            "category",
            "status",
            "priority",
            "deadline",
            "progress",
            "created_at"
        ]

        with open(
            csv_file,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fields
            )

            writer.writeheader()

            for project in projects:

                writer.writerow(
                    project.to_dict()
                )

        logger.info(
            "CSV exported."
        )

        return csv_file

    # ========================================================
    # 📊 STATISTICS
    # ========================================================

    def statistics(self):

        projects = self.get_projects()

        if not projects:

            return {
                "total": 0,
                "completed": 0,
                "in_progress": 0,
                "planned": 0,
                "on_hold": 0,
                "average_progress": 0
            }

        total = len(projects)

        completed = sum(
            project.status == "Completed"
            for project in projects
        )

        in_progress = sum(
            project.status == "In Progress"
            for project in projects
        )

        planned = sum(
            project.status == "Planned"
            for project in projects
        )

        on_hold = sum(
            project.status == "On Hold"
            for project in projects
        )

        average = (
            sum(
                project.progress
                for project in projects
            )
            / total
        )

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "planned": planned,
            "on_hold": on_hold,
            "average_progress": average
        }

    # ========================================================
    # 🧹 CLOSE
    # ========================================================

    def close(self):

        self.database.close()


# ============================================================
# ✅ VALIDATION
# ============================================================

def validate_text(value, field_name):

    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be text."
        )

    if not value.strip():
        raise ValueError(
            f"{field_name} cannot be empty."
        )


def validate_date(value):

    try:

        datetime.strptime(
            value,
            DATE_FORMAT
        )

    except ValueError:

        raise ValueError(
            "Date must use YYYY-MM-DD format."
        )


def validate_progress(value):

    try:

        value = int(value)

    except (
        ValueError,
        TypeError
    ):

        raise ValueError(
            "Progress must be a number."
        )

    if not 0 <= value <= 100:

        raise ValueError(
            "Progress must be between 0 and 100."
        )


def validate_status(value):

    if value not in STATUSES:

        raise ValueError(
            "Invalid status."
        )


def validate_priority(value):

    if value not in PRIORITIES:

        raise ValueError(
            "Invalid priority."
        )


# ============================================================
# 🎨 UI HELPERS
# ============================================================

def print_header(title):

    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def progress_bar(progress, width=25):

    completed = int(
        progress / 100 * width
    )

    remaining = width - completed

    return (
        "█" * completed
        + "░" * remaining
        + f" {progress}%"
    )


def deadline_status(deadline):

    try:

        deadline_date = datetime.strptime(
            deadline,
            DATE_FORMAT
        ).date()

    except ValueError:

        return "⚪ UNKNOWN"

    today = date.today()

    if deadline_date < today:
        return "🔴 OVERDUE"

    if deadline_date == today:
        return "🟡 TODAY"

    return "🟢 UPCOMING"


def display_project(project):

    print()
    print("-" * 70)

    print(f"🆔 ID:          {project.id}")
    print(f"📌 Name:        {project.name}")
    print(f"📝 Description: {project.description}")
    print(f"📂 Category:    {project.category}")
    print(f"📍 Status:      {project.status}")
    print(f"🔥 Priority:    {project.priority}")
    print(f"📅 Deadline:    {project.deadline}")
    print(
        f"⏰ Deadline:    "
        f"{deadline_status(project.deadline)}"
    )

    print(
        f"📈 Progress:    "
        f"{progress_bar(project.progress)}"
    )

    print(f"🕒 Created:     {project.created_at}")

    print("-" * 70)


def show_banner():

    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║                    💼 PROJECTHUB                         ║
║                                                          ║
║              Manage. Build. Achieve. 🚀                  ║
║                                                          ║
║                                                          ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")


def show_menu():

    print("""
╔══════════════════════════════════════════════════════════╗
║                      MAIN MENU                           ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  1.  ➕ Add Project                                       ║
║  2.  📋 Show Projects                                     ║
║  3.  🔍 Search Projects                                   ║
║  4.  ✏️  Update Project                                   ║
║  5.  🗑️  Delete Project                                   ║
║  6.  📊 Statistics                                        ║
║  7.  🔃 Sort Projects                                     ║
║  8.  🎯 Filter Projects                                   ║
║  9.  💾 Export JSON                                       ║
║ 10.  📄 Export CSV                                        ║
║ 11.  📥 Import JSON                                       ║
║ 12.  📦 Create Backup                                     ║
║ 13.  🧪 Run Tests                                         ║
║ 14.  🚪 Exit                                              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")


# ============================================================
# 🔢 INPUT HELPERS
# ============================================================

def get_integer(prompt, minimum=None, maximum=None):

    while True:

        try:

            value = int(
                input(prompt).strip()
            )

            if minimum is not None and value < minimum:

                print(
                    f"⚠️ Minimum value is {minimum}."
                )

                continue

            if maximum is not None and value > maximum:

                print(
                    f"⚠️ Maximum value is {maximum}."
                )

                continue

            return value

        except ValueError:

            print(
                "⚠️ Please enter a valid number."
            )


def get_required_input(prompt):

    while True:

        value = input(prompt).strip()

        if value:

            return value

        print(
            "⚠️ This field cannot be empty."
        )


def choose_option(title, options):

    print(f"\n{title}")

    for index, option in enumerate(
        options,
        start=1
    ):

        print(f"{index}. {option}")

    while True:

        choice = get_integer(
            "Choose: ",
            1,
            len(options)
        )

        return options[choice - 1]


# ============================================================
# ➕ ADD PROJECT UI
# ============================================================

def add_project_ui(service):

    print_header("➕ ADD PROJECT")

    name = get_required_input(
        "Project name: "
    )

    description = get_required_input(
        "Description: "
    )

    category = get_required_input(
        "Category: "
    )

    status = choose_option(
        "📍 STATUS",
        STATUSES
    )

    priority = choose_option(
        "🔥 PRIORITY",
        PRIORITIES
    )

    while True:

        deadline = input(
            "Deadline (YYYY-MM-DD): "
        ).strip()

        try:

            validate_date(deadline)

            break

        except ValueError as error:

            print(f"⚠️ {error}")

    progress = get_integer(
        "Progress (0-100): ",
        0,
        100
    )

    try:

        project = service.create_project(
            name=name,
            description=description,
            category=category,
            status=status,
            priority=priority,
            deadline=deadline,
            progress=progress
        )

        print(
            f"\n✅ Project #{project.id} created!"
        )

    except ValueError as error:

        print(f"\n❌ {error}")


# ============================================================
# 📋 SHOW PROJECTS UI
# ============================================================

def show_projects_ui(service):

    print_header("📋 ALL PROJECTS")

    projects = service.get_projects()

    if not projects:

        print("📭 No projects found.")

        return

    print(
        f"📁 Total: {len(projects)} project(s)"
    )

    for project in projects:

        display_project(project)


# ============================================================
# 🔍 SEARCH UI
# ============================================================

def search_projects_ui(service):

    print_header("🔍 SEARCH PROJECTS")

    keyword = get_required_input(
        "Search keyword: "
    )

    projects = service.search_projects(
        keyword
    )

    if not projects:

        print("❌ No matching projects.")

        return

    print(
        f"\n🔎 Found {len(projects)} project(s)."
    )

    for project in projects:

        display_project(project)


# ============================================================
# ✏️ UPDATE UI
# ============================================================

def update_project_ui(service):

    print_header("✏️ UPDATE PROJECT")

    project_id = get_integer(
        "Project ID: ",
        1
    )

    project = service.get_project(
        project_id
    )

    if project is None:

        print("❌ Project not found.")

        return

    display_project(project)

    print(
        "\nPress ENTER to keep the current value."
    )

    name = input(
        f"Name [{project.name}]: "
    ).strip()

    if name:
        project.name = name

    description = input(
        f"Description [{project.description}]: "
    ).strip()

    if description:
        project.description = description

    category = input(
        f"Category [{project.category}]: "
    ).strip()

    if category:
        project.category = category

    print(
        "\nStatus:"
    )

    for index, status in enumerate(
        STATUSES,
        start=1
    ):

        print(
            f"{index}. {status}"
        )

    status_choice = input(
        f"Status [{project.status}]: "
    ).strip()

    if status_choice:

        try:

            index = int(status_choice)

            if 1 <= index <= len(STATUSES):

                project.status = STATUSES[
                    index - 1
                ]

            else:

                print(
                    "⚠️ Invalid status. "
                    "Old value kept."
                )

        except ValueError:

            print(
                "⚠️ Invalid status. "
                "Old value kept."
            )

    print(
        "\nPriority:"
    )

    for index, priority in enumerate(
        PRIORITIES,
        start=1
    ):

        print(
            f"{index}. {priority}"
        )

    priority_choice = input(
        f"Priority [{project.priority}]: "
    ).strip()

    if priority_choice:

        try:

            index = int(priority_choice)

            if 1 <= index <= len(PRIORITIES):

                project.priority = PRIORITIES[
                    index - 1
                ]

            else:

                print(
                    "⚠️ Invalid priority. "
                    "Old value kept."
                )

        except ValueError:

            print(
                "⚠️ Invalid priority. "
                "Old value kept."
            )

    progress = input(
        f"Progress [{project.progress}%]: "
    ).strip()

    if progress:

        try:

            progress = int(progress)

            validate_progress(progress)

            project.progress = progress

        except ValueError as error:

            print(
                f"⚠️ {error}"
            )

    deadline = input(
        f"Deadline [{project.deadline}]: "
    ).strip()

    if deadline:

        try:

            validate_date(deadline)

            project.deadline = deadline

        except ValueError as error:

            print(
                f"⚠️ {error}"
            )

    try:

        service.update_project(
            project
        )

        print(
            "\n✅ Project updated successfully!"
        )

    except ValueError as error:

        print(
            f"\n❌ {error}"
        )


# ============================================================
# 🗑️ DELETE UI
# ============================================================

def delete_project_ui(service):

    print_header("🗑️ DELETE PROJECT")

    project_id = get_integer(
        "Project ID: ",
        1
    )

    project = service.get_project(
        project_id
    )

    if project is None:

        print("❌ Project not found.")

        return

    display_project(project)

    confirmation = input(
        "\n⚠️ Delete this project? (y/n): "
    ).strip().lower()

    if confirmation != "y":

        print(
            "❌ Deletion cancelled."
        )

        return

    if service.delete_project(
        project_id
    ):

        print(
            "\n✅ Project deleted successfully!"
        )

    else:

        print(
            "\n❌ Project could not be deleted."
        )


# ============================================================
# 📊 STATISTICS UI
# ============================================================

def statistics_ui(service):

    print_header("📊 PROJECT STATISTICS")

    stats = service.statistics()

    if stats["total"] == 0:

        print("📭 No projects available.")

        return

    print(
        f"📁 Total projects:   {stats['total']}"
    )

    print(
        f"✅ Completed:        {stats['completed']}"
    )

    print(
        f"🔄 In Progress:      {stats['in_progress']}"
    )

    print(
        f"📌 Planned:          {stats['planned']}"
    )

    print(
        f"⏸️ On Hold:          {stats['on_hold']}"
    )

    print(
        f"📈 Average progress: "
        f"{stats['average_progress']:.1f}%"
    )

    print(
        "\n🔥 PRIORITY BREAKDOWN"
    )

    projects = service.get_projects()

    for priority in PRIORITIES:

        count = sum(
            project.priority == priority
            for project in projects
        )

        print(
            f"{priority:<12} {count}"
        )

    print(
        "\n📍 STATUS BREAKDOWN"
    )

    for status in STATUSES:

        count = sum(
            project.status == status
            for project in projects
        )

        print(
            f"{status:<15} {count}"
        )


# ============================================================
# 🔃 SORT UI
# ============================================================

def sort_projects_ui(service):

    print_header("🔃 SORT PROJECTS")

    projects = service.get_projects()

    if not projects:

        print("📭 No projects.")

        return

    print("""
1. ID
2. Name
3. Progress
4. Deadline
5. Priority
6. Status
""")

    choice = get_integer(
        "Sort by: ",
        1,
        6
    )

    reverse_choice = input(
        "Descending? (y/n): "
    ).strip().lower()

    reverse = reverse_choice == "y"

    priority_order = {
        "Low": 1,
        "Medium": 2,
        "High": 3,
        "Critical": 4
    }

    status_order = {
        "Planned": 1,
        "In Progress": 2,
        "Completed": 3,
        "On Hold": 4
    }

    if choice == 1:

        projects.sort(
            key=lambda project: project.id,
            reverse=reverse
        )

    elif choice == 2:

        projects.sort(
            key=lambda project: project.name.lower(),
            reverse=reverse
        )

    elif choice == 3:

        projects.sort(
            key=lambda project: project.progress,
            reverse=reverse
        )

    elif choice == 4:

        projects.sort(
            key=lambda project: project.deadline,
            reverse=reverse
        )

    elif choice == 5:

        projects.sort(
            key=lambda project:
            priority_order[project.priority],
            reverse=reverse
        )

    elif choice == 6:

        projects.sort(
            key=lambda project:
            status_order[project.status],
            reverse=reverse
        )

    for project in projects:

        display_project(project)


# ============================================================
# 🎯 FILTER UI
# ============================================================

def filter_projects_ui(service):

    print_header("🎯 FILTER PROJECTS")

    projects = service.get_projects()

    if not projects:

        print("📭 No projects.")

        return

    print("""
1. By Status
2. By Priority
3. By Category
4. Overdue Projects
5. Completed Projects
6. High Priority
""")

    choice = get_integer(
        "Filter by: ",
        1,
        6
    )

    if choice == 1:

        status = choose_option(
            "📍 STATUS",
            STATUSES
        )

        results = [
            project
            for project in projects
            if project.status == status
        ]

    elif choice == 2:

        priority = choose_option(
            "🔥 PRIORITY",
            PRIORITIES
        )

        results = [
            project
            for project in projects
            if project.priority == priority
        ]

    elif choice == 3:

        category = get_required_input(
            "Category: "
        ).lower()

        results = [
            project
            for project in projects
            if category in project.category.lower()
        ]

    elif choice == 4:

        today = date.today()

        results = []

        for project in projects:

            try:

                deadline = datetime.strptime(
                    project.deadline,
                    DATE_FORMAT
                ).date()

                if deadline < today:

                    results.append(project)

            except ValueError:

                continue

    elif choice == 5:

        results = [
            project
            for project in projects
            if project.status == "Completed"
        ]

    else:

        results = [
            project
            for project in projects
            if project.priority in [
                "High",
                "Critical"
            ]
        ]

    if not results:

        print(
            "\n❌ No projects match the filter."
        )

        return

    print(
        f"\n🔎 Found {len(results)} project(s)."
    )

    for project in results:

        display_project(project)


# ============================================================
# 💾 EXPORT JSON UI
# ============================================================

def export_json_ui(service):

    print_header("💾 EXPORT JSON")

    try:

        service.save_json()

        print(
            f"✅ JSON saved to:\n{JSON_FILE}"
        )

    except OSError as error:

        print(
            f"❌ Export failed: {error}"
        )


# ============================================================
# 📄 CSV UI
# ============================================================

def export_csv_ui(service):

    print_header("📄 EXPORT CSV")

    try:

        file_path = service.export_csv()

        print(
            f"✅ CSV exported to:\n{file_path}"
        )

    except OSError as error:

        print(
            f"❌ Export failed: {error}"
        )


# ============================================================
# 📥 IMPORT JSON UI
# ============================================================

def import_json_ui(service):

    print_header("📥 IMPORT JSON")

    try:

        count = service.import_json()

        print(
            f"✅ Imported {count} project(s)."
        )

    except (
        OSError,
        json.JSONDecodeError,
        ValueError,
        KeyError
    ) as error:

        print(
            f"❌ Import failed: {error}"
        )


# ============================================================
# 📦 BACKUP UI
# ============================================================

def backup_ui(service):

    print_header("📦 CREATE BACKUP")

    try:

        backup = service.create_backup()

        print(
            f"✅ Backup created:\n{backup}"
        )

    except OSError as error:

        print(
            f"❌ Backup failed: {error}"
        )


# ============================================================
# 🧪 TESTS
# ============================================================

def run_tests():

    print_header("🧪 PROJECTHUB TESTS")

    # --------------------------------------------------------
    # Test 1 — Project creation
    # --------------------------------------------------------

    project = Project(
        id=999,
        name="Test Project",
        description="Testing",
        category="Test",
        status="Planned",
        priority="High",
        deadline="2099-12-31",
        progress=50
    )

    assert project.id == 999

    print(
        "✅ Project creation test"
    )

    # --------------------------------------------------------
    # Test 2 — Dictionary conversion
    # --------------------------------------------------------

    data = project.to_dict()

    assert data["name"] == "Test Project"
    assert data["progress"] == 50

    print(
        "✅ Dictionary conversion test"
    )

    # --------------------------------------------------------
    # Test 3 — Restoration
    # --------------------------------------------------------

    restored = Project.from_dict(
        data
    )

    assert restored.id == project.id
    assert restored.name == project.name
    assert restored.progress == project.progress

    print(
        "✅ Project restoration test"
    )

    # --------------------------------------------------------
    # Test 4 — Date validation
    # --------------------------------------------------------

    validate_date(
        "2099-12-31"
    )

    print(
        "✅ Date validation test"
    )

    # --------------------------------------------------------
    # Test 5 — Progress validation
    # --------------------------------------------------------

    validate_progress(50)

    print(
        "✅ Progress validation test"
    )

    # --------------------------------------------------------
    # Test 6 — Status validation
    # --------------------------------------------------------

    validate_status(
        "Completed"
    )

    print(
        "✅ Status validation test"
    )

    # --------------------------------------------------------
    # Test 7 — Priority validation
    # --------------------------------------------------------

    validate_priority(
        "Critical"
    )

    print(
        "✅ Priority validation test"
    )

    print()
    print(
        "🎉 ALL TESTS PASSED!"
    )


# ============================================================
# 🚀 MAIN
# ============================================================

def main():

    show_banner()

    service = ProjectService()

    try:

        while True:

            show_menu()

            choice = input(
                "👉 Choose an option: "
            ).strip()

            try:

                if choice == "1":

                    add_project_ui(
                        service
                    )

                elif choice == "2":

                    show_projects_ui(
                        service
                    )

                elif choice == "3":

                    search_projects_ui(
                        service
                    )

                elif choice == "4":

                    update_project_ui(
                        service
                    )

                elif choice == "5":

                    delete_project_ui(
                        service
                    )

                elif choice == "6":

                    statistics_ui(
                        service
                    )

                elif choice == "7":

                    sort_projects_ui(
                        service
                    )

                elif choice == "8":

                    filter_projects_ui(
                        service
                    )

                elif choice == "9":

                    export_json_ui(
                        service
                    )

                elif choice == "10":

                    export_csv_ui(
                        service
                    )

                elif choice == "11":

                    import_json_ui(
                        service
                    )

                elif choice == "12":

                    backup_ui(
                        service
                    )

                elif choice == "13":

                    run_tests()

                elif choice == "14":

                    print()
                    print(
                        "=" * 60
                    )
                    print(
                        "👋 Thank you for using PROJECTHUB!"
                    )
                    print(
                        "🚀 Manage. Build. Achieve."
                    )
                    print(
                        "=" * 60
                    )

                    break

                else:

                    print(
                        "\n⚠️ Invalid option."
                    )

            except sqlite3.Error as error:

                logger.error(
                    "Database error: %s",
                    error
                )

                print(
                    f"\n❌ Database error: {error}"
                )

            except OSError as error:

                logger.error(
                    "System error: %s",
                    error
                )

                print(
                    f"\n❌ System error: {error}"
                )

    finally:

        service.close()


# ============================================================
# ▶️ ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()