'use client';

import { useState, useEffect } from 'react';
import { Key, AlertTriangle, CheckCircle, Lock } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from '@/components/ui/use-toast';
import { Button } from '@/components/ui/button';
import { LoadingButton } from '@/components/ui/loading-button';
import { Input } from '@/components/ui/input';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { PasswordStrengthMeter } from '@/components/ui/password-strength-meter';
import { MasterPasswordUnlockModal } from '@/components/ui/master-password-unlock-modal';
import { FormErrorSummary } from '@/components/ui/form-error-summary';
import { useUnlock } from '@/contexts/unlock-context';
import apiClient, {
  MasterPasswordRotateSchema,
  KeyRotationEstimateSchema,
  type MasterPasswordRotate,
  type KeyRotationEstimate,
  type KeyRotationStatus,
} from '@/lib/api-client';
import { getErrorMessage, isUnauthorizedError } from '@/lib/error-handler';
import { clearMasterSessionToken } from '@/lib/auth';

export default function KeyRotationPage() {
  const [estimate, setEstimate] = useState<KeyRotationEstimate | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRotating, setIsRotating] = useState(false);
  const [rotationResult, setRotationResult] =
    useState<KeyRotationStatus | null>(null);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isNewPasswordValid, setIsNewPasswordValid] = useState(false);
  const [showUnlockModal, setShowUnlockModal] = useState(false);
  const [pendingRotation, setPendingRotation] =
    useState<MasterPasswordRotate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [postRotationUnlockMessage, setPostRotationUnlockMessage] =
    useState<string | null>(null);

  const { requireUnlock, isUnlocked, forceLock } = useUnlock();

  const form = useForm<MasterPasswordRotate>({
    resolver: zodResolver(MasterPasswordRotateSchema),
    defaultValues: {
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
    mode: 'onChange',
  });
  const errorMessages = Object.values(form.formState.errors)
    .map((error) => error?.message)
    .filter((message): message is string => Boolean(message));

  useEffect(() => {
    loadEstimate();
  }, []);

  const loadEstimate = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.getRotationEstimate();
      setEstimate(KeyRotationEstimateSchema.parse(data));
    } catch (err) {
      const errorMessage = getErrorMessage(err, 'key rotation estimate');
      setError(errorMessage);

      // If it's an unauthorized error, show unlock modal instead of toast
      if (isUnauthorizedError(err) && !isUnlocked) {
        setShowUnlockModal(true);
      } else {
        toast({
          title: 'Error',
          description: errorMessage,
          variant: 'destructive',
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const validateCurrentPassword = async (password: string) => {
    try {
      const response = await apiClient.validateCurrentPassword(password);
      return response.valid;
    } catch {
      return false;
    }
  };

  const onSubmit = async (data: MasterPasswordRotate) => {
    // Validate new password meets policy requirements
    if (!isNewPasswordValid) {
      toast({
        title: 'Weak Password',
        description:
          'The new password does not meet security requirements. Please ensure it meets all the requirements listed.',
        variant: 'destructive',
      });
      return;
    }

    // Check if master password is unlocked
    const canProceed = requireUnlock(() => executeRotation(data));
    if (!canProceed) {
      setPendingRotation(data);
      setShowUnlockModal(true);
    }
  };

  const executeRotation = async (data: MasterPasswordRotate) => {
    // Validate current password first
    const isCurrentPasswordValid = await validateCurrentPassword(
      data.current_password
    );
    if (!isCurrentPasswordValid) {
      toast({
        title: 'Invalid Password',
        description: 'The current master password is incorrect',
        variant: 'destructive',
      });
      return;
    }

    setIsRotating(true);
    try {
      const result = await apiClient.rotateMasterPassword(data);
      setRotationResult(result);

      if (result.failed_devices === 0) {
        form.reset();
        setIsNewPasswordValid(false);
        setPendingRotation(null);

        // If session was invalidated, logout and prompt for new password
        if (result.session_invalidated) {
          clearMasterSessionToken();
          forceLock();
          setPostRotationUnlockMessage(
            'Your master password has been rotated. Please unlock with your new password to continue.'
          );
          setShowUnlockModal(true);
          toast({
            title: 'Success',
            description: `Successfully rotated master password for ${result.rotated_devices} devices. Please unlock with your new password.`,
          });
        } else {
          toast({
            title: 'Success',
            description: `Successfully rotated master password for ${result.rotated_devices} devices`,
          });
        }
      } else {
        toast({
          title: 'Partial Success',
          description: `Rotation completed with ${result.failed_devices} failure${result.failed_devices === 1 ? '' : 's'}`,
          variant: 'destructive',
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description:
          error instanceof Error
            ? error.message
            : 'Failed to rotate master password',
        variant: 'destructive',
      });
    } finally {
      setIsRotating(false);
    }
  };

  const handleUnlockSuccess = () => {
    setShowUnlockModal(false);
    if (pendingRotation) {
      executeRotation(pendingRotation);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-3">
        <Key className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold">Key Rotation</h1>
          <p className="text-muted-foreground">
            Rotate the master password and re-encrypt all stored WireGuard keys
          </p>
        </div>
      </div>

      {estimate && (
        <Card>
          <CardHeader>
            <CardTitle>Rotation Estimate</CardTitle>
            <CardDescription>
              Overview of items that will be processed during key rotation
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-success-border bg-success-surface p-4 text-center">
                <div className="text-2xl font-bold text-success">
                  {estimate.total_devices}
                </div>
                <div className="text-sm font-medium text-success-foreground">
                  Devices
                </div>
              </div>
              <div className="rounded-lg border border-warning-border bg-warning-surface p-4 text-center">
                <div className="text-2xl font-bold text-warning">
                  {estimate.total_keys}
                </div>
                <div className="text-sm font-medium text-warning-foreground">
                  Total Keys
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {error && (
        <Alert
          variant={isUnauthorizedError(error) ? 'default' : 'destructive'}
          className={isUnauthorizedError(error) ? 'border-primary' : ''}
        >
          {isUnauthorizedError(error) && <Lock className="h-4 w-4" />}
          <AlertDescription className="ml-2">
            {error}
            {isUnauthorizedError(error) && !isUnlocked && (
              <Button
                variant="link"
                className="ml-2 p-0 h-auto"
                onClick={() => setShowUnlockModal(true)}
              >
                Unlock Now
              </Button>
            )}
          </AlertDescription>
        </Alert>
      )}

      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          <strong>Warning:</strong> Key rotation is a critical operation that
          will re-encrypt all stored private keys. Ensure you have a backup
          before proceeding. The operation cannot be undone.
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle>Rotate Master Password</CardTitle>
          <CardDescription>
            Enter your current master password and choose a new one to rotate
            all encrypted keys
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormErrorSummary messages={errorMessages} />
              <FormField
                control={form.control}
                name="current_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Current Master Password</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type={showCurrentPassword ? 'text' : 'password'}
                          placeholder="Enter current master password"
                          {...field}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-0 top-0 h-full px-3 py-2"
                          onClick={() =>
                            setShowCurrentPassword(!showCurrentPassword)
                          }
                        >
                          {showCurrentPassword ? 'Hide' : 'Show'}
                        </Button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="new_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>New Master Password</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type={showNewPassword ? 'text' : 'password'}
                          placeholder="Enter new master password"
                          {...field}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-0 top-0 h-full px-3 py-2"
                          onClick={() => setShowNewPassword(!showNewPassword)}
                        >
                          {showNewPassword ? 'Hide' : 'Show'}
                        </Button>
                      </div>
                    </FormControl>
                    <FormMessage />
                    {field.value && (
                      <div className="mt-2">
                        <PasswordStrengthMeter
                          password={field.value}
                          onValidationChange={setIsNewPasswordValid}
                          showPolicy={true}
                        />
                      </div>
                    )}
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="confirm_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Confirm New Password</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type={showConfirmPassword ? 'text' : 'password'}
                          placeholder="Confirm new master password"
                          {...field}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-0 top-0 h-full px-3 py-2"
                          onClick={() =>
                            setShowConfirmPassword(!showConfirmPassword)
                          }
                        >
                          {showConfirmPassword ? 'Hide' : 'Show'}
                        </Button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Separator />

              <div className="flex justify-end">
                <LoadingButton
                  type="submit"
                  loading={isRotating}
                  disabled={isLoading || !isNewPasswordValid}
                  loadingText="Rotating..."
                  className="min-w-32"
                >
                  <Key className="mr-2 h-4 w-4" />
                  Rotate Master Password
                </LoadingButton>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>

      {rotationResult && (
        <Card>
          <CardHeader>
            <CardTitle>Rotation Results</CardTitle>
            <CardDescription>
              Summary of the key rotation operation
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-3">
                <h4 className="flex items-center font-semibold text-success">
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Successfully Rotated
                </h4>
                <div className="pl-6 space-y-2">
                  <div className="flex justify-between">
                    <span>Devices:</span>
                    <Badge variant="secondary">
                      {rotationResult.rotated_devices}
                    </Badge>
                  </div>
                </div>
              </div>

              {rotationResult.failed_devices > 0 && (
                <div className="space-y-3">
                  <h4 className="flex items-center font-semibold text-destructive">
                    <AlertTriangle className="mr-2 h-4 w-4" />
                    Failed to Rotate
                  </h4>
                  <div className="pl-6 space-y-2">
                    <div className="flex justify-between">
                      <span>Devices:</span>
                      <Badge variant="destructive">
                        {rotationResult.failed_devices}
                      </Badge>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {rotationResult.errors.length > 0 && (
              <>
                <Separator />
                <div>
                  <h4 className="mb-2 font-semibold text-destructive">
                    Errors
                  </h4>
                  <div className="space-y-2">
                    {rotationResult.errors.map((error, index) => (
                      <Alert key={index} variant="destructive">
                        <AlertDescription>{error}</AlertDescription>
                      </Alert>
                    ))}
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}

      <MasterPasswordUnlockModal
        isOpen={showUnlockModal}
        onClose={() => {
          setShowUnlockModal(false);
          setPendingRotation(null);
          setPostRotationUnlockMessage(null);
        }}
        onSuccess={handleUnlockSuccess}
        title={
          postRotationUnlockMessage
            ? 'Unlock with New Password'
            : 'Master Password Required for Key Rotation'
        }
        description={
          postRotationUnlockMessage ||
          'Enter the master password to unlock key rotation capabilities. This is required to decrypt and re-encrypt all stored private keys.'
        }
      />
    </div>
  );
}
