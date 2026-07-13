package skill0.runtime

import rego.v1

default decision := {"outcome": "deny", "reason": "no matching policy"}

decision := {"outcome": "allow", "reason": "read-only action"} if {
    input.effect.classification == "read_only"
}

decision := {"outcome": "require_approval", "reason": "destructive write"} if {
    input.effect.classification == "destructive_write"
    not input.context.approved
}

decision := {"outcome": "allow", "reason": "approved destructive write"} if {
    input.effect.classification == "destructive_write"
    input.context.approved
}
