package scas.ci

deny contains msg if {
  input.on.pull_request_target
  msg := sprintf("workflow '%s': pull_request_target trigger is forbidden", [input.name])
}

deny contains msg if {
  input.permissions == "write-all"
  msg := sprintf("workflow '%s': write-all permissions are forbidden", [input.name])
}

deny contains msg if {
  input.permissions == {}
  msg := sprintf("workflow '%s': empty permissions block is forbidden", [input.name])
}

deny contains msg if {
  some job_name, job in input.jobs
  some step in job.steps
  ref := step.uses
  startswith(ref, "actions/")
  not regex.match("@[0-9a-f]{40}$", ref)
  msg := sprintf("workflow '%s' job '%s': action '%s' must be pinned to a full SHA", [input.name, job_name, ref])
}

deny contains msg if {
  some job_name, job in input.jobs
  some step in job.steps
  ref := step.uses
  startswith(ref, "docker://")
  not contains(ref, "@sha256:")
  msg := sprintf("workflow '%s' job '%s': docker image '%s' must be digest-pinned", [input.name, job_name, ref])
}
