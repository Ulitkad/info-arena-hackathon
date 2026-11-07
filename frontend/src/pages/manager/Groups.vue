<script setup>
import { inject } from 'vue';
import { roleName } from '../../api';
import Icon from '../../components/Icon.vue';
import Avatar from '../../components/Avatar.vue';
const manager = inject('manager-page');
const { store, route, router, tab, catalog, members, requests, invites, rewards, modal, loading, search, message, groupName, subjectName, subjectColor, inviteGroup, assign, editingTeacher, inviteRole, renameTarget, renameName, reward, editRewardId, organizations, inviteUrl, organizationId, filteredMembers, pendingByGroup, studentCount, load, chooseOrganization, perform, routeTab, createGroup, createSubject, saveLinks, toggleLink, invite, moderate, copyInvite, approveAll, openTeacher, saveTeacherLoads, deleteMember, deleteTeacher, saveReward, editReward, deleteReward, openRename, saveRename } = manager;
</script>

<template>
<section class="management-content">
      <div class="section-head">
        <div>
          <span class="eyebrow">СТРУКТУРА УЧРЕЖДЕНИЯ</span>
          <h2>Учебные группы и предметы</h2>
        </div>
        <div class="button-row">
          <button class="btn secondary small" @click="modal = 'subject'">
            <Icon name="plus" :size="15" />Предмет</button
          ><button class="btn primary small" @click="modal = 'group'">
            <Icon name="plus" :size="15" />Группа
          </button>
        </div>
      </div>
      <div class="catalog-grid">
        <section class="catalog-column">
          <div class="catalog-heading">
            <span class="eyebrow">ГРУППЫ</span
            ><span class="subtle-count">{{ catalog.groups.length }}</span>
          </div>
          <article
            v-for="group in catalog.groups"
            :key="group.id"
            class="catalog-row"
          >
            <span class="catalog-symbol"><Icon name="users" :size="17" /></span
            ><span class="catalog-row-main"
              ><strong>{{ group.name }}</strong
              ><small
                >{{
                  members.filter((m) => m.group_id === group.id).length
                }}
                участников</small
              ><span class="linked-subjects">{{
                catalog.links
                  .filter((l) => l.group_id === group.id)
                  .map(
                    (l) =>
                      catalog.subjects.find((s) => s.id === l.subject_id)?.name,
                  )
                  .filter(Boolean)
                  .join(" · ") || "Предметы пока не выбраны"
              }}</span></span
            ><button
              class="icon-btn"
              :aria-label="`Пригласить ученика в ${group.name}`"
              @click="assign.group_id = String(group.id); modal = 'invite-student'"
            ><Icon name="link" :size="16" /></button><button
              class="icon-btn"
              :aria-label="`Переименовать ${group.name}`"
              @click="openRename(group, 'group')"
            >
              <Icon name="pencil" :size="16" /></button
            ><button
              class="icon-btn"
              :aria-label="`Настроить предметы ${group.name}`"
              @click="
                inviteGroup = group;
                modal = `links:${group.id}`;
              "
            >
              <Icon name="settings" :size="17" />
            </button>
          </article>
          <p v-if="!catalog.groups.length" class="empty-inline">
            Создай первую учебную группу.
          </p>
        </section>
        <section class="catalog-column">
          <div class="catalog-heading">
            <span class="eyebrow">ПРЕДМЕТЫ</span
            ><span class="subtle-count">{{ catalog.subjects.length }}</span>
          </div>
          <article
            v-for="subject in catalog.subjects"
            :key="subject.id"
            class="catalog-row"
          >
            <span class="subject-dot" :style="{ background: subject.color }"
              ><Icon name="book" :size="15" /></span
            ><span class="catalog-row-main"
              ><strong>{{ subject.name }}</strong
              ><small
                >{{
                  catalog.links.filter((l) => l.subject_id === subject.id)
                    .length
                }}
                учебных групп</small
              ></span
            ><button
              class="icon-btn"
              :aria-label="`Переименовать ${subject.name}`"
              @click="openRename(subject, 'subject')"
            >
              <Icon name="pencil" :size="16" />
            </button>
          </article>
          <p v-if="!catalog.subjects.length" class="empty-inline">
            Добавь предметы, чтобы назначить нагрузку.
          </p>
        </section>
      </div>
      <div class="student-list-head">
        <div>
          <span class="eyebrow">УЧАСТНИКИ</span>
          <h3>
            Ученики и преподаватели
            <span class="inline-count">{{ filteredMembers.length }}</span>
          </h3>
        </div>
        <div class="member-actions">
          <label class="search-field"
            ><Icon name="search" :size="16" /><input
              v-model="search"
              placeholder="Поиск по имени или группе" /></label
          ><button class="btn primary small" @click="modal = 'invite-student'">
            <Icon name="user-plus" :size="15" />Добавить
          </button>
        </div>
      </div>
      <article
        v-for="member in filteredMembers"
        :key="member.id"
        class="member-row panel"
      >
        <Avatar :user="member" :size="40" />
        <div class="request-user">
          <strong>{{ member.display_name }}</strong
          ><span>@{{ member.username || member.max_id }}</span>
        </div>
        <span class="role-chip small-role">{{ roleName(member.role) }}</span
        ><span v-if="member.group_id" class="member-group">{{
          catalog.groups.find((g) => g.id === member.group_id)?.name || "Группа"
        }}</span
        ><button
          v-if="member.role === 'STUDENT' && member.group_id"
          class="icon-btn danger-icon"
          aria-label="Удалить ученика из группы"
          @click="deleteMember(member)"
        >
          <Icon name="trash" :size="17" />
        </button>
      </article>
      <p v-if="!filteredMembers.length" class="empty-inline">
        Участников не найдено.
      </p>
    </section>

</template>
