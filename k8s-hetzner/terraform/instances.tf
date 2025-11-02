locals {
  master = {
    node1 = {
      name       = "1"
      datacenter = "nbg1-dc3"
    }
    node2 = {
      name       = "2"
      datacenter = "hel1-dc2"
    }
  }
  worker = {
    node1 = {
      name       = "1"
      datacenter = "nbg1-dc3"
    }
    node2 = {
      name       = "2"
      datacenter = "nbg1-dc3"
    }
    node3 = {
      name       = "3"
      datacenter = "nbg1-dc3"
    }
    node4 = {
      name       = "4"
      datacenter = "nbg1-dc3"
    }

  }
}


resource "hcloud_server" "master" {
  for_each = local.master

  name        = "master-${each.value.name}"
  image       = "ubuntu-24.04"
  server_type = "cpx21"

  public_net {
    ipv4_enabled = true
    ipv6_enabled = true
  }

  datacenter = each.value.datacenter

  labels = {
    "node-role.kubernetes.io/master" = "true"
  }

  user_data = templatefile("template/userdata.yaml", {
    name = each.value.name
  })

  ssh_keys = ["ATPstealer"]
}

resource "hcloud_server" "worker" {
  for_each = local.worker

  name        = "worker-${each.value.name}"
  image       = "ubuntu-24.04"
  server_type = "cpx31"

  public_net {
    ipv4_enabled = true
    ipv6_enabled = true
  }

  datacenter = each.value.datacenter

  labels = {
    "node-role.kubernetes.io/worker" = "true"
  }

  user_data = templatefile("template/userdata.yaml", {
    name = each.value.name
  })

  ssh_keys = ["ATPstealer"]
}