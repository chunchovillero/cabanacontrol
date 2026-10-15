from apps.audit.models import AuditEvent


def record_event(*, actor, action, entity, entity_id="", tenant=None, before=None, after=None):
    return AuditEvent.objects.create(
        actor=actor,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        tenant=tenant,
        before=before or {},
        after=after or {},
    )
