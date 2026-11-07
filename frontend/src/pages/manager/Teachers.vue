<script setup>
import { inject } from 'vue';
import Icon from '../../components/Icon.vue';
import Avatar from '../../components/Avatar.vue';
import { remove } from '../../api';
const manager = inject('manager-page');
const { store, route, router, tab, catalog, members, requests, invites, rewards, modal, loading, search, message, groupName, subjectName, subjectColor, inviteGroup, assign, editingTeacher, inviteRole, renameTarget, renameName, reward, editRewardId, organizations, inviteUrl, organizationId, filteredMembers, pendingByGroup, studentCount, load, chooseOrganization, perform, routeTab, createGroup, createSubject, saveLinks, toggleLink, invite, moderate, copyInvite, approveAll, openTeacher, saveTeacherLoads, deleteMember, deleteTeacher, saveReward, editReward, deleteReward, openRename, saveRename } = manager;
</script>

<template>
<section class="management-content">
      <div class="section-head">
        <div>
          <span class="eyebrow">ПРЕПОДАВАТЕЛЬСКИЙ СОСТАВ</span>
          <h2>Преподаватели и нагрузка</h2>
        </div>
        <button
          class="btn primary"
          @click="openTeacher()"
        >
          <Icon name="link" :size="16" />Пригласить преподавателя
        </button>
      </div>
      <div class="teacher-load-grid">
        <article
          v-for="person in members.filter((m) => m.role === 'TEACHER')"
          :key="person.id"
          class="teacher-load-card panel"
        >
          <div class="teacher-load-profile">
            <Avatar :user="person" :size="46" />
            <div>
              <strong>{{ person.display_name }}</strong
              ><span>@{{ person.username || person.max_id }}</span>
            </div>
            <button
              class="icon-btn"
              :aria-label="`Изменить нагрузку ${person.display_name}`"
              @click="openTeacher(person)"
            >
              <Icon name="pencil" :size="16" />
            </button><button
              class="icon-btn danger-icon"
              :aria-label="`Удалить преподавателя ${person.display_name}`"
              @click="deleteTeacher(person)"
            >
              <Icon name="trash" :size="16" />
            </button>
          </div>
          <div
            v-for="subject in [
              ...new Set(
                catalog.loads
                  .filter((l) => l.teacher_id === person.id)
                  .map((l) => l.subject_id),
              ),
            ]
              .map((id) => catalog.subjects.find((s) => s.id === id))
              .filter(Boolean)"
            :key="subject.id"
            class="load-subject"
          >
            <span :style="{ background: subject.color }"></span
            ><strong>{{ subject.name }}</strong
            ><small>{{
              catalog.loads
                .filter(
                  (l) =>
                    l.teacher_id === person.id && l.subject_id === subject.id,
                )
                .map(
                  (l) => catalog.groups.find((g) => g.id === l.group_id)?.name,
                )
                .filter(Boolean)
                .join(", ")
            }}</small>
          </div>
        </article>
        <div
          v-if="!members.some((m) => m.role === 'TEACHER')"
          class="empty-page panel"
        >
          <span class="empty-icon"><Icon name="graduation" :size="27" /></span>
          <h3>Учителей пока нет</h3>
          <p>Выбери учебную нагрузку и пригласи преподавателя по одноразовой ссылке.</p>
          <button
            class="btn primary small"
            @click="openTeacher()"
          >
            <Icon name="plus" :size="15" />Добавить
          </button>
        </div>
      </div>
      <div class="invites-list">
        <div class="catalog-heading">
          <span class="eyebrow">ПРИГЛАШЕНИЯ ПРЕПОДАВАТЕЛЯМ</span>
        </div>
        <article
          v-for="invite in invites.filter((i) => i.role === 'TEACHER')"
          :key="invite.id"
          class="invite-row"
        >
          <span class="catalog-symbol"><Icon name="link" :size="16" /></span
          ><span
            ><strong>{{
              invite.loads.map(l => `${catalog.subjects.find(s => s.id === l.subject_id)?.name || 'Предмет удалён'} · ${catalog.groups.find(g => g.id === l.group_id)?.name || 'Группа удалена'}`).join(', ')
            }}</strong
            ><small>{{
              invite.revoked
                ? "ОТЗЫВАНО"
                : invite.used_by
                  ? "ИСПОЛЬЗОВАНО"
                  : "АКТИВНО"
            }}</small></span
          ><button
            v-if="!invite.revoked && !invite.used_by"
            class="icon-btn danger-icon"
            aria-label="Отозвать приглашение"
            @click="
              perform(
                () => remove(`/invites/${invite.id}`),
                'Приглашение отозвано',
              )
            "
          >
            <Icon name="x" :size="16" />
          </button>
        </article>
      </div>
    </section>

</template>
