# GitHub Actions for Augustan

## Kanban Board Automation

This directory contains GitHub Actions workflows that automate project management for the Augustan trading bot.

### Kanban Sync Workflow

**File**: `.github/workflows/kanban-sync.yml`

**Purpose**: Automatically syncs `TODO.md` with GitHub Project Board

**Triggers**:
- Push to `main`/`master` branch when `TODO.md` changes
- Pull requests affecting `TODO.md`
- Manual workflow dispatch

**Features**:
- ✅ Parses `TODO.md` for tasks and milestones
- ✅ Creates/updates GitHub Issues automatically
- ✅ Organizes tasks in Project Board columns (To Do, In Progress, Done)
- ✅ Closes completed tasks automatically
- ✅ Adds milestone-based labels

### Setup Instructions

1. **Enable GitHub Actions** in your repository settings
2. **Create Project Board** (optional - will be created automatically)
3. **Push changes** to `TODO.md` to trigger sync

### Project Board Structure

- **To Do**: Open tasks from `TODO.md`
- **In Progress**: Tasks currently being worked on
- **Done**: Completed tasks (marked with `[x]` in `TODO.md`)

### Benefits

- 📋 **Automated Project Management**: No manual board updates needed
- 🔄 **Single Source of Truth**: `TODO.md` drives everything
- 📊 **Visual Progress Tracking**: GitHub Project Board provides visual overview
- 🏷️ **Organized by Milestones**: Tasks automatically labeled by milestone
- ⚡ **Real-time Sync**: Updates happen on every push

### Usage

Simply update your `TODO.md` file:

```markdown
### [x] Task 1.1: Completed Task
### [ ] Task 1.2: Pending Task
```

The GitHub Action will automatically:
1. Create GitHub Issues for new tasks
2. Close Issues for completed tasks
3. Update the Project Board
4. Apply appropriate labels

No manual intervention required!
