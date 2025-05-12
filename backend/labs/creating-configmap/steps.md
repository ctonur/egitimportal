# Lab: Creating a ConfigMap

This lab will guide you through creating and using ConfigMaps in OpenShift/Kubernetes.

## Step 1

Create a ConfigMap named `app-config` in the `nextapp` namespace with the following content:

```bash
oc create configmap app-config --from-literal=environment=production --from-literal=log-level=info -n nextapp
```

## Step 2

Add a file named `config.json` to the existing ConfigMap with the following content:

```bash
echo '{"cache": true, "timeout": 5000}' > config.json
oc create configmap app-config --from-file=config.json -n nextapp --dry-run=client -o yaml | oc replace -f -
```

## Step 3

View the contents of the ConfigMap to verify both the key-value pairs and the file were added:

```bash
oc get configmap app-config -o yaml -n nextapp
```

## Step 4

Create a Pod that mounts the ConfigMap as a volume:

```bash
cat <<EOF | oc apply -n nextapp -f -
apiVersion: v1
kind: Pod
metadata:
  name: configmap-pod
spec:
  containers:
    - name: app
      image: registry.access.redhat.com/ubi8/ubi-minimal:8.3
      command: ["sleep", "3600"]
      volumeMounts:
      - name: config-volume
        mountPath: /etc/config
  volumes:
    - name: config-volume
      configMap:
        name: app-config
EOF
```

## Step 5

Verify that the ConfigMap is mounted as a volume in the Pod:

```bash
oc exec -n nextapp configmap-pod -- ls -la /etc/config
```