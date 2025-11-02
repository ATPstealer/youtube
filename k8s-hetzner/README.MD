### [YouTube instruction rus](https://www.youtube.com/watch?v=B9mdoVmsy6U)

## [K8s install](https://psj.codes/creating-a-kubernetes-cluster-with-kubeadm-and-containerd-a-comprehensive-step-by-step-guide)

1) Terraform apply
2) DNS setup for master nodes
3) Make it on one
   of [master node](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/high-availability/):
    ```aiignore
    kubeadm init --control-plane-endpoint "k8s-best.atpstealer.com:6443" --upload-certs --pod-network-cidr=10.244.0.0/16
    kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml
    ```
4) Connect other nodes and label worker with role:
   ```aiignore
   kubectl label nodes worker-1 role=worker
   ```
5) [Metallb](https://metallb.universe.tf/configuration/_advanced_ipaddresspool_configuration/)
    ```
    helm repo add metallb https://metallb.github.io/metallb
    helm upgrade -n metallb-system --create-namespace --install metallb metallb/metallb 
    ```
   apply IP pool
6) [CSI Driver](https://github.com/0hlov3/kubernetes-on-hetzner/blob/main/README.md#install-container-storage-interface-driver-csi-driver)
     ```aiignore
     kubectl -n kube-system create secret generic hcloud-csi --from-literal=token=<hcloud API token>
     kubectl apply -f https://raw.githubusercontent.com/hetznercloud/csi-driver/v1.6.0/deploy/kubernetes/hcloud-csi.yml
     ```
   Verify (not necessary) if volume exist after
     ```
     kubectl apply -f https://raw.githubusercontent.com/0hlov3/kubernetes-on-hetzner/main/test-deployment/csi-pvc-test.yaml
     ```

## [GitLab](https://docs.gitlab.com/charts/installation/deployment.html)

Setup DNS record for gitlab wildcard domain zone.

```aiignore
helm repo add gitlab https://charts.gitlab.io/
helm repo update
helm upgrade -n gitlab --create-namespace --install gitlab gitlab/gitlab --timeout 600s --set global.hosts.domain=gl.atpstealer.com --set global.hosts.externalIP=167.235.56.111 --set certmanager-issuer.email=forpubmail@gmail.com --set global.edition=ce
```

## Ingress

```agsl
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress ingress-nginx/ingress-nginx --namespace ingress-nginx  --create-namespace  --set controller.service.loadBalancerIP=188.245.158.57
```

## Cluster issuer

```agsl
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.8.2/cert-manager.yaml
kubectl apply -f issuer-lets-encrypt.yaml
```

## GitLab runner access

```
kubectl apply -f gitlab-rolebinding.yaml
```